from __future__ import annotations


PILOT_CONTENT = {
    "skills": [
        {
            "skill_id": "fraction_partwhole_g4_01",
            "curriculum": "CAPS",
            "grade": 4,
            "term": 1,
            "strand": "Number, Operations and Relationships",
            "topic": "Fractions",
            "subtopic": "Fractions as part of a whole",
            "name": "Identify fractions as part of a whole",
            "description": "Learner identifies shaded fractions using simple visual and symbolic forms.",
            "caps_code": "G4-T1-FRA-PW-01",
            "difficulty_bands_supported": ["support", "core", "stretch"],
            "recommended_question_types": ["visual", "multiple_choice"],
            "prerequisite_skill_ids": [],
            "misconception_tags": ["swap_numerator_denominator", "counts_unshaded"],
        },
        {
            "skill_id": "add_regroup_g4_01",
            "curriculum": "CAPS",
            "grade": 4,
            "term": 1,
            "strand": "Number, Operations and Relationships",
            "topic": "Addition",
            "subtopic": "Addition with regrouping",
            "name": "Add numbers with regrouping",
            "description": "Learner adds two-digit numbers and explains regrouping.",
            "caps_code": "G4-T1-ADD-RG-01",
            "difficulty_bands_supported": ["support", "core", "stretch"],
            "recommended_question_types": ["direct", "fill_blank", "multiple_choice"],
            "prerequisite_skill_ids": [],
            "misconception_tags": ["ignore_carry", "place_value_confusion", "digit_reversal"],
        },
    ],
    "templates": [
        {
            "template_id": "tpl_add_regroup_direct_01",
            "template_code": "add_regroup_direct_01",
            "skill_id": "add_regroup_g4_01",
            "family_id": "add_regroup_family",
            "name": "Two-digit addition with regrouping",
            "question_type": "direct",
            "template_text": "{a} + {b} = __",
            "variable_schema": {
                "a": {"type": "int", "required": True},
                "b": {"type": "int", "required": True}
            },
            "difficulty_profiles": {
                "support": {"a_range": [11, 49], "b_range": [11, 49]},
                "core": {"a_range": [11, 79], "b_range": [11, 79]},
                "stretch": {"a_range": [11, 99], "b_range": [11, 99]}
            },
            "constraints": [
                {"type": "expression", "rule": "a % 10 + b % 10 >= 10"},
                {"type": "expression", "rule": "a + b <= 150"}
            ],
            "answer_formula": {"type": "expression", "value": "a + b"},
            "distractor_rules": [
                {"type": "ignore_carry"},
                {"type": "off_by_ten"},
                {"type": "digit_reversal"}
            ],
            "explanation_template": "Add the ones first. Regroup if needed. Then add the tens.",
            "rendering": {"visual_type": None, "layout_hint": "single_line"},
            "theme_supported": False,
            "visual_supported": False,
            "misconception_targets": ["ignore_carry", "place_value_confusion", "digit_reversal"],
            "active": True
        },
        {
            "template_id": "tpl_add_regroup_missing_01",
            "template_code": "add_regroup_missing_01",
            "skill_id": "add_regroup_g4_01",
            "family_id": "add_regroup_family",
            "name": "Missing addend with regrouping",
            "question_type": "fill_blank",
            "template_text": "{a} + __ = {total}",
            "variable_schema": {
                "a": {"type": "int", "required": True},
                "b": {"type": "int", "required": True},
                "total": {"type": "int", "required": True}
            },
            "difficulty_profiles": {
                "support": {"a_range": [10, 39], "b_range": [11, 39]},
                "core": {"a_range": [10, 59], "b_range": [11, 59]},
                "stretch": {"a_range": [10, 89], "b_range": [11, 89]}
            },
            "constraints": [
                {"type": "expression", "rule": "a % 10 + b % 10 >= 10"},
                {"type": "expression", "rule": "a + b <= 160"}
            ],
            "answer_formula": {"type": "expression", "value": "b"},
            "distractor_rules": [
                {"type": "ignore_carry"},
                {"type": "off_by_one"},
                {"type": "off_by_ten"}
            ],
            "explanation_template": "Find the missing addend by subtracting the known addend from the total.",
            "rendering": {"visual_type": None, "layout_hint": "single_line"},
            "theme_supported": False,
            "visual_supported": False,
            "misconception_targets": ["ignore_carry", "place_value_confusion"],
            "active": True
        },
        {
            "template_id": "tpl_fraction_partwhole_visual_01",
            "template_code": "fraction_partwhole_visual_01",
            "skill_id": "fraction_partwhole_g4_01",
            "family_id": "fraction_partwhole_family",
            "name": "Identify shaded fraction from bar model",
            "question_type": "visual",
            "template_text": "What fraction of the shape is shaded?",
            "variable_schema": {
                "parts_total": {"type": "int", "required": True},
                "parts_shaded": {"type": "int", "required": True}
            },
            "difficulty_profiles": {
                "support": {"parts_total_values": [2, 3, 4, 5, 6]},
                "core": {"parts_total_values": [2, 3, 4, 5, 6, 8]},
                "stretch": {"parts_total_values": [2, 3, 4, 5, 6, 8, 10, 12]}
            },
            "constraints": [
                {"type": "expression", "rule": "parts_shaded >= 1"},
                {"type": "expression", "rule": "parts_shaded < parts_total"}
            ],
            "answer_formula": {"type": "fraction", "numerator": "parts_shaded", "denominator": "parts_total"},
            "distractor_rules": [
                {"type": "swap_num_den"},
                {"type": "use_unshaded_as_numerator"},
                {"type": "off_by_one_shaded"}
            ],
            "explanation_template": "The numerator shows shaded parts. The denominator shows total equal parts.",
            "rendering": {"visual_type": "fraction_bar", "layout_hint": "full_width"},
            "theme_supported": False,
            "visual_supported": True,
            "misconception_targets": ["swap_numerator_denominator", "counts_unshaded"],
            "active": True
        },
        {
            "template_id": "tpl_fraction_partwhole_mcq_01",
            "template_code": "fraction_partwhole_mcq_01",
            "skill_id": "fraction_partwhole_g4_01",
            "family_id": "fraction_partwhole_family",
            "name": "Choose the correct shaded fraction",
            "question_type": "multiple_choice",
            "template_text": "Choose the fraction that matches the shaded parts: {parts_shaded} shaded out of {parts_total}.",
            "variable_schema": {
                "parts_total": {"type": "int", "required": True},
                "parts_shaded": {"type": "int", "required": True}
            },
            "difficulty_profiles": {
                "support": {"parts_total_values": [2, 3, 4, 5, 6]},
                "core": {"parts_total_values": [3, 4, 5, 6, 8]},
                "stretch": {"parts_total_values": [4, 5, 6, 8, 10, 12]}
            },
            "constraints": [
                {"type": "expression", "rule": "parts_shaded >= 1"},
                {"type": "expression", "rule": "parts_shaded < parts_total"}
            ],
            "answer_formula": {"type": "fraction", "numerator": "parts_shaded", "denominator": "parts_total"},
            "distractor_rules": [
                {"type": "swap_num_den"},
                {"type": "use_unshaded_as_numerator"},
                {"type": "simplified_wrong"}
            ],
            "explanation_template": "Use shaded parts for the numerator and total parts for the denominator.",
            "rendering": {"visual_type": None, "layout_hint": "single_line"},
            "theme_supported": False,
            "visual_supported": False,
            "misconception_targets": ["swap_numerator_denominator", "counts_unshaded"],
            "active": True
        }
    ],
    "blueprints": [
        {
            "blueprint_id": "bp_concept_default",
            "worksheet_type": "concept",
            "question_count": 20,
            "sections": [
                {
                    "section_id": "warmup",
                    "title": "Warm-Up",
                    "target_count": 4,
                    "difficulty_bias": "support",
                    "question_types": ["visual", "fill_blank"],
                    "template_family_bias": ["fraction_partwhole_family", "add_regroup_family"],
                    "instructions": "Start with guided questions."
                },
                {
                    "section_id": "core",
                    "title": "Core Practice",
                    "target_count": 12,
                    "difficulty_bias": "core",
                    "question_types": ["direct", "fill_blank", "multiple_choice", "visual"],
                    "template_family_bias": ["fraction_partwhole_family", "add_regroup_family"],
                    "instructions": "Show what you know."
                },
                {
                    "section_id": "challenge",
                    "title": "Challenge",
                    "target_count": 4,
                    "difficulty_bias": "stretch",
                    "question_types": ["direct", "multiple_choice", "visual"],
                    "template_family_bias": ["fraction_partwhole_family", "add_regroup_family"],
                    "instructions": "Try the trickier questions."
                }
            ]
        },
        {
            "blueprint_id": "bp_fluency_default",
            "worksheet_type": "fluency",
            "question_count": 20,
            "sections": [
                {
                    "section_id": "practice",
                    "title": "Practice",
                    "target_count": 16,
                    "difficulty_bias": "support",
                    "question_types": ["direct", "fill_blank", "multiple_choice"],
                    "template_family_bias": ["add_regroup_family", "fraction_partwhole_family"],
                    "instructions": "Work quickly and carefully."
                },
                {
                    "section_id": "review",
                    "title": "Review",
                    "target_count": 4,
                    "difficulty_bias": "core",
                    "question_types": ["direct", "fill_blank", "multiple_choice"],
                    "template_family_bias": ["add_regroup_family", "fraction_partwhole_family"],
                    "instructions": "Finish with mixed review."
                }
            ]
        }
    ]
}

