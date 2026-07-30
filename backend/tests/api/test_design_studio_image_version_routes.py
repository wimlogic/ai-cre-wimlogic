from app.main import app


def test_design_image_version_list_route_is_registered():
    route = app.openapi()["paths"]["/api/v1/design-studio/image-versions/"]
    assert "get" in route
