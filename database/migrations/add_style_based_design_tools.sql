-- =============================================================================
-- add_style_based_design_tools.sql
--
-- AIHOME Design Studio - Style-Based Tools.
--
-- Adds new style-based Design Tools (Spanish Mediterranean, European
-- Classic, Italian Stucco, Japanese Bamboo) ALONGSIDE the existing
-- room-based tools (Exterior Remodel, etc.) - per explicit "not sure
-- yet" on replace-vs-add, this is the safe, fully reversible default.
-- Nothing is deleted or deactivated; Exterior/Interior Remodel remain
-- exactly as they are.
--
-- Each new Tool gets:
--   - One generic Image Requirement: input_role='reference',
--     min_count=1, max_count=9, no allowed_image_roles_json
--     restriction - the user may freely mix kitchen/living/exterior
--     photos in one job, since room identity already lives on each
--     Property Image's own image_role, not on the Tool.
--   - One Tool Option: a selectable color_palette (per this session's
--     explicit answer: "a selectable color palette option per style").
--
-- workflow_code is set but, per the locked WACP routing architecture,
-- is NEVER read at dispatch time - business_intent="IMAGE_DESIGN_ONLY"
-- is what DEV-TOOLS actually routes on for every Design Studio
-- submission, regardless of which Tool. The column remains NOT NULL on
-- cre_design_tools, so a value is still required; it carries no
-- functional weight.
--
-- Retiring a Tool later (if "replace entirely" is eventually decided)
-- is a one-line `UPDATE ... SET status='inactive'` - never a DELETE,
-- to preserve any DesignJob history that already references it.
-- =============================================================================


-- SECTION 1 - PRE-MIGRATION VERIFICATION

SELECT id, tool_code, tool_name, design_type, workflow_code, status
FROM cre_design_tools
ORDER BY display_order;

SELECT COUNT(*) AS tools_count_before FROM cre_design_tools;


-- SECTION 2 - INSERT THE FOUR NEW STYLE TOOLS

INSERT INTO cre_design_tools
  (tool_code, tool_name, design_type, workflow_code, business_description,
   business_purpose, business_instructions, status, display_order)
VALUES
  ('STYLE_SPANISH_MEDITERRANEAN', 'Spanish Mediterranean', 'PROPERTY_REDESIGN', 'WF_STYLE_DESIGN',
   'Apply a Spanish Mediterranean design language across the selected images.',
   'Visualize a Spanish Mediterranean style transformation before analysis and estimation.',
   'Preserve the property''s primary geometry unless configured otherwise.',
   'active', 100),
  ('STYLE_EUROPEAN_CLASSIC', 'European Classic', 'PROPERTY_REDESIGN', 'WF_STYLE_DESIGN',
   'Apply a European Classic design language across the selected images.',
   'Visualize a European Classic style transformation before analysis and estimation.',
   'Preserve the property''s primary geometry unless configured otherwise.',
   'active', 101),
  ('STYLE_ITALIAN_STUCCO', 'Italian Stucco', 'PROPERTY_REDESIGN', 'WF_STYLE_DESIGN',
   'Apply an Italian Stucco design language across the selected images.',
   'Visualize an Italian Stucco style transformation before analysis and estimation.',
   'Preserve the property''s primary geometry unless configured otherwise.',
   'active', 102),
  ('STYLE_JAPANESE_BAMBOO', 'Japanese Bamboo', 'PROPERTY_REDESIGN', 'WF_STYLE_DESIGN',
   'Apply a Japanese Bamboo design language across the selected images.',
   'Visualize a Japanese Bamboo style transformation before analysis and estimation.',
   'Preserve the property''s primary geometry unless configured otherwise.',
   'active', 103);


-- SECTION 3 - IMAGE REQUIREMENTS: 1 to 9 images, any room, per new Tool

INSERT INTO cre_design_tool_image_requirements
  (tool_id, input_role, allowed_image_roles_json, min_count, max_count, display_order)
SELECT id, 'reference', NULL, 1, 9, 1
FROM cre_design_tools
WHERE tool_code IN (
  'STYLE_SPANISH_MEDITERRANEAN', 'STYLE_EUROPEAN_CLASSIC',
  'STYLE_ITALIAN_STUCCO', 'STYLE_JAPANESE_BAMBOO'
);


-- SECTION 4 - COLOR PALETTE OPTION per new Tool
-- A starting palette list per style - easily adjusted later since this
-- is pure data, not code. is_required=0 with a sensible default so a
-- job can still be generated without the user explicitly picking one.

INSERT INTO cre_design_tool_options
  (tool_id, option_code, option_label, option_type, allowed_values_json,
   default_value, is_required, display_order, status)
SELECT id, 'color_palette', 'Color Palette', 'select',
  '["Warm Terracotta", "Sun-Bleached Neutral", "Deep Ocean Blue", "Olive & Sand"]',
  'Warm Terracotta', 0, 1, 'active'
FROM cre_design_tools WHERE tool_code = 'STYLE_SPANISH_MEDITERRANEAN';

INSERT INTO cre_design_tool_options
  (tool_id, option_code, option_label, option_type, allowed_values_json,
   default_value, is_required, display_order, status)
SELECT id, 'color_palette', 'Color Palette', 'select',
  '["Warm Neutral", "Cool Gray", "Muted Sage", "Classic Cream"]',
  'Warm Neutral', 0, 1, 'active'
FROM cre_design_tools WHERE tool_code = 'STYLE_EUROPEAN_CLASSIC';

INSERT INTO cre_design_tool_options
  (tool_id, option_code, option_label, option_type, allowed_values_json,
   default_value, is_required, display_order, status)
SELECT id, 'color_palette', 'Color Palette', 'select',
  '["Tuscan Ochre", "Warm Ivory", "Weathered Terracotta", "Soft Sienna"]',
  'Tuscan Ochre', 0, 1, 'active'
FROM cre_design_tools WHERE tool_code = 'STYLE_ITALIAN_STUCCO';

INSERT INTO cre_design_tool_options
  (tool_id, option_code, option_label, option_type, allowed_values_json,
   default_value, is_required, display_order, status)
SELECT id, 'color_palette', 'Color Palette', 'select',
  '["Natural Bamboo", "Charcoal & Bamboo", "Moss Green", "Warm Sand"]',
  'Natural Bamboo', 0, 1, 'active'
FROM cre_design_tools WHERE tool_code = 'STYLE_JAPANESE_BAMBOO';


-- SECTION 5 - POST-MIGRATION VERIFICATION

SELECT id, tool_code, tool_name, design_type, workflow_code, status, display_order
FROM cre_design_tools
ORDER BY display_order;
-- Expect the 4 original tools PLUS the 4 new style tools, all active.

SELECT t.tool_code, r.input_role, r.min_count, r.max_count
FROM cre_design_tool_image_requirements r
JOIN cre_design_tools t ON t.id = r.tool_id
WHERE t.tool_code LIKE 'STYLE_%';
-- Expect min_count=1, max_count=9 for all 4 new tools.

SELECT t.tool_code, o.option_code, o.option_label, o.default_value
FROM cre_design_tool_options o
JOIN cre_design_tools t ON t.id = o.tool_id
WHERE t.tool_code LIKE 'STYLE_%';
-- Expect one color_palette option per new tool.

SELECT COUNT(*) AS tools_count_after FROM cre_design_tools;
-- Must be exactly 4 more than SECTION 1's count.


-- SECTION 6 - ROLLBACK (only if genuinely needed; safe since these are
-- brand-new rows with no DesignJob history yet)

-- DELETE FROM cre_design_tool_options WHERE tool_id IN
--   (SELECT id FROM cre_design_tools WHERE tool_code LIKE 'STYLE_%');
-- DELETE FROM cre_design_tool_image_requirements WHERE tool_id IN
--   (SELECT id FROM cre_design_tools WHERE tool_code LIKE 'STYLE_%');
-- DELETE FROM cre_design_tools WHERE tool_code LIKE 'STYLE_%';

-- =============================================================================
-- END OF FILE
-- =============================================================================
