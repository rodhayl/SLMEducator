# Returned course/material defects: offline repair evidence

Date: 2026-10-08. Source baseline: `16a2dd9ba84fbaf103aff056fee8b07372c5102e`.
The historical report in `auto_testing_2026-10-08_001/DEFECTS.md` remains unchanged.

## Scope and changes

- **SLM-AUTO-002:** Distinguish an actually empty authorized library from a filter
  hiding existing materials. Staff see first-material guidance and the existing
  creation/generation actions; learners see availability guidance. An empty
  library no longer offers a reset button that cannot change the result.
- **SLM-AUTO-003:** Use the established form/Field validation boundary to identify
  both duplicate option keys, retain input, and focus the first invalid field.
  Empty option text, insufficient choices, and a no-longer-valid correct-answer
  key also have relevant validation feedback. Existing payload validation remains.
- **SLM-AUTO-006:** Display stable course IDs on list cards and in shared course
  selector options. List links describe their course ID accessibly without
  replacing the teacher-authored title. Sources and generation share this selector.
- **SLM-AUTO-007:** Hide blank optional lesson fields, lists, vocabulary entries,
  and sections. Preserve nonempty material, clarification order, sanitization,
  and the de-duplication of canonical flattened content, including an empty section
  between two populated sections.
- **SLM-AUTO-012:** Associate distinct empty-file, unsupported-type, and oversized
  file errors with the file input using both catalogs. Rejection occurs before a
  request and leaves the existing source unchanged. A later valid file clears the
  error but still requires explicit adoption and saving.
- **SLM-AUTO-013:** Body-only lesson normalization no longer invents persisted
  English “Lesson”/“Overview” section titles. Untitled sections render their text
  without an empty heading. The teacher's lesson title remains on the page.
- **Related SLM-AUTO-001 cases:** Independently reproduced rapid-input loss in
  course and material search. Both now use the router's synchronous update option,
  already supported by the application's RouterProvider. Tests use the same callback.

All new user-facing strings have English and Spanish entries. No dependencies,
shared error-display primitives, authorization, or publication boundaries changed.

## Reproduction before changes

`course-material-defects.test.tsx` initially produced **16 failures and 2 passes**,
covering the six assigned report defects in both languages. New schema tests
initially produced **4 failures and 7 passes** in `test_lesson_visible_fields.py`.

Separate burst-typing tests reproduced “Same title” becoming “e” in course search
and “Practice” becoming “e” in material search before their respective fixes.

A later additional regression found duplicate paragraph rendering when an empty
middle section was hidden; the renderer was corrected before final verification.

## Verification

The regression file covers both locales, corrected resubmission, invalid file
preservation, maximum-size/uppercase-extension acceptance, role-specific empty
states, stable course identity, rapid search input, and canonical body de-duplication.

Final verification: **213 frontend tests passed in 10 files**, including **25**
new defect regressions. **118 Python tests passed** in seven affected files.
Frontend TypeScript and scoped ESLint passed. Python flake8 passed for the two
changed Python files; mypy passed for `content_schema.py`.

```bash
npm test --prefix src/frontend -- --reporter=dot tests/frontend/course-material-defects.test.tsx tests/frontend/authoring-contracts.test.ts tests/frontend/authoring-flows.test.tsx tests/frontend/learning-reading.test.tsx tests/frontend/course-list-continuity.test.tsx tests/frontend/courses-contracts.test.ts tests/frontend/courses-navigation.test.tsx tests/frontend/courses-workflows.test.tsx tests/frontend/learning-source-clarification-fixtures.test.tsx tests/frontend/learning-locale-continuity.test.tsx
npm run typecheck --prefix src/frontend
SLM_OFFLINE_TESTS=1 USE_REAL_AI=0 python -m pytest tests/test_lesson_visible_fields.py tests/trust/test_content_ingress_contract.py tests/trust/test_content_service_storage.py tests/trust/test_lesson_source_review.py tests/trust/test_lesson_instruction_consistency.py tests/trust/test_product_journeys.py tests/trust/test_generation_sources.py -q --basetemp=/tmp/slm-course-affected-python-2
python -m flake8 src/core/services/content_schema.py tests/test_lesson_visible_fields.py
python -m mypy src/core/services/content_schema.py
```

ESLint covered the eight changed feature files and all three changed frontend
test files. The pre-existing authoring fixture warning for an undefined generation
jobs read remains; it did not fail the suite. The Python run reported one dependency
deprecation warning. Tests use synthetic API mocks or disposable databases and
offline provider transport.

## Boundaries

- No real model/provider call, native Windows packaging, live browser acceptance,
  user database, or user computer was used for this repair.
- Historical stored section titles remain verbatim. Older automatically inserted
  “Lesson” text has no marker distinguishing it from a deliberately authored title;
  the repair does not guess or rewrite existing teaching content.
- These scoped checks do not establish whole-source coverage, full integration
  acceptance, or native executable readiness.
