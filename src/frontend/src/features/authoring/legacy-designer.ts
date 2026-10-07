import { authoredSource, generationDefaults, identifier, isGenerationDraft, isSourceDocument, isSourceInput, record, sourceInput, type GenerationDraft, type Outline } from './contracts';

/** Translate only the historical designer fields. The original entry is never removed. */
export function legacyDesignerSetup(value: unknown): GenerationDraft | null {
 if (!record(value) || !record(value.currentConfig)) return null;
 const config = value.currentConfig;
 if (config.subject !== undefined && typeof config.subject !== 'string' || config.grade_level !== undefined && typeof config.grade_level !== 'string' || config.duration !== undefined && (!Number.isInteger(config.duration) || Number(config.duration) < 1 || Number(config.duration) > 104)) return null;
 if (value.createdStudyPlanId != null && !identifier(value.createdStudyPlanId)) return null;
 const createdPlanId = identifier(value.createdStudyPlanId) ? value.createdStudyPlanId : null;
 const hasTasks = Array.isArray(value.generationTasks) && value.generationTasks.length > 0;
 let outline: Outline | null = null;
 if (value.generatedOutline != null) {
  const old = value.generatedOutline;
  if (!record(old) || typeof old.title !== 'string' || old.description !== undefined && typeof old.description !== 'string' || !Array.isArray(old.units) || old.units.length > 101) return null;
  const units: Outline['units'] = [];
  for (const unit of old.units) {
   if (!record(unit) || typeof unit.title !== 'string' || !Array.isArray(unit.lessons) || unit.lessons.length > 1001) return null;
   const lessons: Outline['units'][number]['lessons'] = [];
   for (const lesson of unit.lessons) {
    if (!record(lesson) || typeof lesson.title !== 'string' || lesson.learning_objectives !== undefined && (!Array.isArray(lesson.learning_objectives) || !lesson.learning_objectives.every(item => typeof item === 'string'))) return null;
    lessons.push({ title: lesson.title, learning_objectives: lesson.learning_objectives as string[] | undefined || [], selected: !createdPlanId && !hasTasks });
   }
   units.push({ title: unit.title, lessons });
  }
  outline = { title: old.title, description: typeof old.description === 'string' ? old.description : '', units };
 }
 if (value.generationTasks !== undefined && !Array.isArray(value.generationTasks)) return null;
 const taskIds = new Set<string>();
 for (const task of Array.isArray(value.generationTasks) ? value.generationTasks : []) {
  if (!record(task) || !Number.isInteger(task.unit) || !Number.isInteger(task.lesson) || !['pending', 'running', 'saved', 'failed'].includes(String(task.status))) return null;
  const lesson = outline?.units[Number(task.unit)]?.lessons[Number(task.lesson)];
  const taskId = `${task.unit}:${task.lesson}`;
  if (!lesson || taskIds.has(taskId)) return null;
  taskIds.add(taskId);
  // Saved topics stay deselected; interrupted requests are never automatically replayed.
  lesson.selected = task.status !== 'saved';
  if (!lesson.learning_objectives.length) lesson.learning_objectives = [`Understand ${lesson.title}`];
 }
 const coverage = value.sourceCoverage;
 const sourceText = typeof value.sourceMaterialText === 'string' ? value.sourceMaterialText : record(coverage) && typeof coverage.extracted_text === 'string' ? coverage.extracted_text : '';
 if (sourceText.length > 100000) return null;
 const recoveredSource = sourceText.trim() ? isSourceDocument(coverage) && coverage.extracted_text === sourceText ? sourceInput(coverage) : isSourceInput(coverage) && coverage.extracted_text === sourceText ? coverage : authoredSource(record(coverage) && typeof coverage.filename === 'string' ? coverage.filename : 'recovered-source.txt', sourceText) : null;
 const candidate: GenerationDraft = { form: { ...generationDefaults, mode: 'outline', subject: typeof config.subject === 'string' ? config.subject : '', grade: typeof config.grade_level === 'string' ? config.grade_level : '', weeks: typeof config.duration === 'number' ? config.duration : 4, planId: createdPlanId ? String(createdPlanId) : '' }, outline, createdPlanId, recoveredSource };
 return isGenerationDraft(candidate) ? candidate : null;
}
