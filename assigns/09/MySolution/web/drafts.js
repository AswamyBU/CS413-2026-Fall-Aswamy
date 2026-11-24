// Pure helpers for unsaved-edit tracking (no DOM).

export function programDraft(program) {
  return { name: program?.name ?? "", description: program?.description ?? "", source: program?.source ?? "" };
}

export function collectionDraft(collection) {
  return { name: collection?.name ?? "", description: collection?.description ?? "" };
}

export function caseDraft(testCase) {
  const e = testCase?.expected ?? { kind: "value", value: "" };
  return {
    name: testCase?.name ?? "",
    source: testCase?.source ?? "",
    description: testCase?.description ?? "",
    kind: e.kind,
    value: e.kind === "value" ? e.value : "",
    category: e.kind === "error" ? e.category : "syntax",
  };
}

export function caseFromDraft(d) {
  return {
    name: d.name,
    source: d.source,
    description: d.description,
    expected: d.kind === "value" ? { kind: "value", value: d.value } : { kind: "error", category: d.category },
  };
}

// A draft is dirty when any field differs from the saved baseline.
export function isDirty(draft, baseline) {
  if (!draft) return false;
  return Object.keys(draft).some((k) => draft[k] !== baseline[k]);
}
