# Independent design review — round 1

## Scope and conclusion

Reviewed only `SKILL.md` against the stated goal: explanations of code, concepts, and ideas that are quickly understandable, compact, technically faithful, and adapted to the reader. I did not inspect evaluation cases, rubrics, generated responses, or test artifacts.

The design is usable as written. I found no blocking problem. One evidence-related wording change deserves priority; three small edits would make the defaults more internally consistent. These are design judgments, not evidence that the skill passes an empirical evaluation.

## Ranked findings

### 1. Important — distinguish source-established behavior from behavior observed during execution

**Location:** §2, “Explain observed behavior confidently.”

**Risk:** The surrounding instructions correctly distinguish source facts from inferred intent, but “observed behavior” is ambiguous after an instruction to inspect source. Reading a conditional, configuration lookup, or call to an external service establishes what the code can do under stated conditions; it does not establish which branch executed, the deployed configuration, or the service’s actual response. An explanation could become more confident than its evidence supports while appearing to follow this sentence.

**Minimal correction:** Replace the sentence with: “State behavior established by the inspected source plainly; qualify outcomes that depend on missing inputs, configuration, dependencies, or runtime evidence.” Keep the existing instruction about inferred intent.

**Confidence:** 0.86 that this clarification would reduce a real technical-explanation failure mode. Other fidelity rules already mitigate the risk, so this is not a blocker.

### 2. Optional — make the unfamiliar-reader assumption explicitly conditional

**Location:** §1, “Treat them as capable and unfamiliar with this topic”; §4, “Keep standard terminology for an expert.”

**Risk:** The skill correctly tells the assistant to infer knowledge and skip demonstrated basics. However, its unconditional unfamiliar-reader instruction competes with its expert-audience instruction. In a short expert question, the assistant may waste words defining familiar concepts or recast a precise question at too elementary a level.

**Minimal correction:** Change the default to: “When the conversation gives no audience signal, assume a capable reader who is new to this topic.” Retain the instructions to infer knowledge and skip demonstrated basics.

**Confidence:** 0.93. This removes a wording tension without adding a new workflow.

### 3. Optional — make examples optional in every statement of the rule

**Location:** Opening paragraph, “recognize it in a concrete example”; §3 table, the “What is it?” row; §3 worked-example bullet.

**Risk:** The worked-example bullet sensibly says to use an example when it helps. The opening and table can instead be read as requiring an example for every explanation. That can produce an unnecessary extra sentence or section in a tiny definition, exact code question, or direct misconception correction.

**Minimal correction:** Add “when useful” to the opening’s example clause and change the table entry to “one concrete example if helpful.” No additional rule is needed.

**Confidence:** 0.92. The existing “select only the pieces” and short-answer defaults mitigate the inconsistency.

### 4. Optional — let the opening encompass reasoning as well as mechanisms

**Location:** Opening paragraph, “follow the mechanism.”

**Risk:** The trigger scope includes ideas and concepts, but the top-level success criterion emphasizes mechanisms. In literary interpretation, a philosophical argument, a definition, or an explanation of a disputed claim, the useful object may be a line of reasoning or distinction rather than a mechanism. A literal reading can encourage an unnecessary process explanation.

**Minimal correction:** Replace “follow the mechanism” with “follow the relevant reasoning or mechanism.” The existing structure table can remain short and non-exhaustive.

**Confidence:** 0.88. This is a scope-alignment refinement rather than a major omission.

## Strengths

1. **The skill connects simplicity to fidelity.** Source inspection, preservation of identifiers and conditions, attention to execution order and failure paths, and the final check against misleading simplification give useful constraints on what may be shortened. These provisions are more actionable than a general request to “be clear.”

2. **Its output conventions support quick comprehension without a teaching ceremony.** It starts with the answer, limits headings and table cells, defines unfamiliar terms inline, prefers a single worked example, and explicitly avoids unsolicited quizzes, repeated conclusions, and continuation invitations. The rule to change the explanation when confusion persists is also practical.

## Coverage check

| Review area | Assessment |
| --- | --- |
| Trigger scope | Broad enough for code, concepts, comparisons, and ideas; implementation-only and ordinary copyediting exclusions are clear. |
| Contradictory rules | No hard contradiction; reader assumptions and example requirements have minor wording tensions described above. |
| Oversimplification | Strong protection through conditions, branches, errors, units, uncertainty, and misconception correction. |
| Information overload | Strong defaults; avoid expanding the skill with exhaustive domain lists or mandatory explanation templates. |
| Evidence handling | Good overall; clarify source inspection versus runtime observation. |
| Contextual adaptation | Good overall; make the novice default conditional rather than apparently universal. |
| Likely practical failures | Overconfident runtime claims, unnecessary beginner definitions or examples, and occasional forced mechanism framing. These are plausible risks, not observed test failures. |

**Overall confidence:** 0.90 in the design assessment.

**Key caveats:** This was a static review of one skill file. I have not measured activation accuracy, answer quality, brevity, or behavior under a specific surrounding system prompt. No claim of empirical test success is made.
