from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.crud.property_image import property_image as crud_property_image
from app.crud.property import property as crud_property
from app.schemas.property_image import PropertyImageCreate, PropertyImageUpdate
from app.models.property_image import PropertyImage

class PropertyImageService:
    def get_image(self, db: Session, id: int) -> Optional[PropertyImage]:
        """Retrieve a property image by its database primary key ID."""
        return crud_property_image.get(db, id)

    def get_images(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        property_id: Optional[int] = None,
        project_id: Optional[str] = None,
        image_type: Optional[str] = None,
        include_deleted: bool = False,
        search: Optional[str] = None
    ) -> Tuple[List[PropertyImage], int]:
        """Get a list of property images with pagination and multiple filtering options."""
        return crud_property_image.get_multi(
            db,
            skip=skip,
            limit=limit,
            property_id=property_id,
            project_id=project_id,
            image_type=image_type,
            include_deleted=include_deleted,
            search=search
        )

    def create_image(self, db: Session, image_in: PropertyImageCreate) -> PropertyImage:
        """
        Create a new property image entry. A request that explicitly asks
        for both is_deleted=1 and is_primary=1 is rejected outright - a
        deleted image can never be primary, and this is an explicit,
        contradictory request rather than something to silently normalize.

        When the request explicitly sets is_primary=1 (and is_deleted is
        not also 1), this routes through the same authoritative
        primary-clearing rule as update_image()/set_primary_image() below -
        see _clear_other_primaries() - so a newly created image can never
        coexist with an existing primary image for the same property.
        is_primary=0 or omitted continues through the plain create path
        unchanged.
        """
        if image_in.is_primary == 1 and image_in.is_deleted == 1:
            raise ValueError("A Property Image cannot be created as both deleted and primary")
        if image_in.is_primary != 1:
            return crud_property_image.create(db, obj_in=image_in)
        try:
            # Lock the EFFECTIVE target Property row FOR UPDATE before any
            # write in this transaction - this is the serialization
            # boundary that makes the one-primary-image invariant safe
            # under concurrent requests targeting the same property, not
            # just atomic within a single request.
            crud_property.lock_for_update(db, image_in.property_id)
            new_obj = crud_property_image.create(db, obj_in=image_in, commit=False)
            self._clear_other_primaries(db, property_id=new_obj.property_id, exclude_id=new_obj.id, commit=False)
            db.commit()
            db.refresh(new_obj)
            return new_obj
        except Exception:
            db.rollback()
            raise

    def _clear_other_primaries(self, db: Session, *, property_id: int, exclude_id: int, commit: bool = False) -> int:
        """
        THE single authoritative primary-clearing operation. Every path
        that can result in a Property Image becoming primary - create,
        update, and the explicit set-primary action - calls this exact
        method (directly or via _set_primary_transaction below) rather
        than re-implementing the property-scoped clearing rule. Always
        scopes to property_id and only clears OTHER non-deleted images -
        never touches any other property's rows (cross-property safety).

        property_id here must always be the image's EFFECTIVE TARGET
        property - i.e. the property it will belong to AFTER the write,
        not necessarily the property it belonged to before. Callers are
        responsible for resolving that effective property_id (see
        update_image()'s effective_property_id computation) before calling
        this method - this method itself has no notion of "before" vs
        "after", it only ever clears within the one property_id it's given.
        """
        return crud_property_image.clear_primary_for_property(
            db, property_id=property_id, exclude_id=exclude_id, commit=commit
        )

    def _set_primary_transaction(
        self, db: Session, *, db_obj: PropertyImage, obj_in: Optional[PropertyImageUpdate] = None, effective_property_id: Optional[int] = None
    ) -> PropertyImage:
        """
        Authoritative transaction for making an EXISTING row primary.
        update_image() (when the resulting/effective is_primary is 1) and
        set_primary_image() (the explicit POST .../set-primary action)
        both route through this exact method, which itself calls the
        shared _clear_other_primaries() helper above - the same helper
        create_image() calls for the create-time case. There is only one
        property-scoped clearing rule in the codebase, reused by all
        three call sites.

        effective_property_id is the property the image will belong to
        AFTER this write - it is the caller's responsibility to compute
        this correctly (falling back to db_obj.property_id when the
        request does not move the image to a different property). Primary
        clearing is scoped to THIS property, never to db_obj's prior
        property_id if those two differ - a Property Image that is moving
        to a new Property and becoming primary there must not touch the
        old Property's primary image at all.

        Sequence (one atomic transaction):
            1. Lock the EFFECTIVE target Property row FOR UPDATE - this is
               the serialization boundary. Two concurrent requests
               targeting the same property's primary image will have one
               block behind the other here, rather than both racing
               through the clear-then-set sequence independently.
            2. Clear is_primary on every OTHER non-deleted image for the
               EFFECTIVE target property only.
            3. Apply the update to the target row (any other changed
               fields from obj_in, plus is_primary forced to 1).
            4. Commit once. On any failure, roll back - the prior primary
               image (in whichever property it belongs to) must remain
               unchanged, and the Property row lock is released.
        """
        property_id = effective_property_id if effective_property_id is not None else db_obj.property_id
        try:
            crud_property.lock_for_update(db, property_id)
            self._clear_other_primaries(db, property_id=property_id, exclude_id=db_obj.id, commit=False)
            merged = obj_in if obj_in is not None else PropertyImageUpdate(is_primary=1)
            if merged.is_primary != 1:
                # Safety net: this transaction must always end with the
                # target row as the primary image, regardless of what was
                # passed in.
                merged = merged.model_copy(update={"is_primary": 1})
            updated = crud_property_image.update(db, db_obj=db_obj, obj_in=merged, commit=False)
            db.commit()
            db.refresh(updated)
            return updated
        except Exception:
            db.rollback()
            raise

    def update_image(self, db: Session, id: int, image_in: PropertyImageUpdate) -> Optional[PropertyImage]:
        """
        Update fields of an existing property image by database primary
        key ID.

        Two invariants are enforced here, ahead of the normal update path:

        1. DELETED IMAGES CANNOT BE PRIMARY. effective_is_deleted is
           resolved as (incoming is_deleted if supplied, else the row's
           current is_deleted). If the request explicitly asks for
           is_primary=1 while the effective result is deleted=1, that is
           an explicit, contradictory request and is rejected with
           ValueError (mapped to HTTP 400 by the router) rather than
           silently normalized - this covers both "already-deleted row,
           now asked to become primary" and "deleting and setting primary
           coincide" cases. If the effective result is merely deleted=1
           without an explicit is_primary=1 request (e.g. a plain soft
           delete of a currently-primary image, or an update to an
           already-deleted row that doesn't touch is_primary), is_primary
           is silently forced to 0 - deletion intent, not a primary
           request, was actually expressed.

        2. PRIMARY CLEARING FOLLOWS THE IMAGE'S EFFECTIVE TARGET PROPERTY,
           NOT ITS PRIOR PROPERTY. effective_is_primary is resolved as
           (incoming is_primary if supplied, else the row's current
           is_primary) - this is what makes "move Image A to Property 2
           without touching is_primary, while A was already primary in
           Property 1" still correctly clear Property 2's existing
           primary (not Property 1's, and not skip clearing entirely just
           because is_primary wasn't explicitly in this particular
           request). effective_property_id is resolved the same way
           (incoming property_id if supplied, else the row's current
           property_id) and is what _set_primary_transaction() actually
           clears against.
        """
        db_obj = crud_property_image.get(db, id)
        if not db_obj:
            return None

        effective_is_deleted = image_in.is_deleted if image_in.is_deleted is not None else db_obj.is_deleted

        if image_in.is_primary == 1 and effective_is_deleted == 1:
            raise ValueError("A deleted Property Image cannot be set as primary")

        if effective_is_deleted == 1:
            image_in = image_in.model_copy(update={"is_primary": 0})
            return crud_property_image.update(db, db_obj=db_obj, obj_in=image_in)

        effective_is_primary = image_in.is_primary if image_in.is_primary is not None else db_obj.is_primary
        if effective_is_primary == 1:
            effective_property_id = image_in.property_id if image_in.property_id is not None else db_obj.property_id
            return self._set_primary_transaction(db, db_obj=db_obj, obj_in=image_in, effective_property_id=effective_property_id)

        return crud_property_image.update(db, db_obj=db_obj, obj_in=image_in)

    def set_primary_image(self, db: Session, id: int) -> Optional[PropertyImage]:
        """
        Explicit "set as primary" action. Refuses a soft-deleted image
        outright (ValueError, mapped to HTTP 400 by the router) - a
        deleted image can never become primary through any path. For a
        non-deleted image, routes through the exact same
        _set_primary_transaction() as update_image() above, scoped to the
        image's current property_id (this action never moves an image
        between properties, so there is no "effective" property to
        resolve here - it is always the row's own property_id).
        """
        db_obj = crud_property_image.get(db, id)
        if not db_obj:
            return None
        if db_obj.is_deleted == 1:
            raise ValueError("A deleted Property Image cannot be set as primary")
        return self._set_primary_transaction(db, db_obj=db_obj, obj_in=None, effective_property_id=db_obj.property_id)

    def delete_image(self, db: Session, id: int, soft: bool = True) -> Optional[PropertyImage]:
        """
        Delete an image by database ID. Supports soft deleting (setting
        is_deleted to 1) or hard removal. Soft delete always forces
        is_primary=0 in the same single-row update, regardless of the
        row's current is_primary value - a deleted image cannot remain the
        Property's primary visual image, and no replacement primary is
        automatically selected (the Property may temporarily have none).
        This does not need the multi-row primary-clearing transaction,
        since it only ever clears the target row's own flag, never
        another row's.
        """
        db_obj = crud_property_image.get(db, id)
        if not db_obj:
            return None
        
        if soft:
            update_in = PropertyImageUpdate(is_deleted=1, is_primary=0)
            return crud_property_image.update(db, db_obj=db_obj, obj_in=update_in)
        else:
            # Perform actual database hard deletion
            return crud_property_image.remove(db, id=id)

property_image_service = PropertyImageService()
