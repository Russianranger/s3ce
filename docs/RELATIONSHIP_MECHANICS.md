# Romantic relationship mechanics: research and proposed change

The user confirms the delivered Hot Smooch fix worked and reports no subsequent
crashes (2026-11-15, referring to 0.1.15 by conversation context). Preserve that
working release. This investigation concerns romantic progression with **Luke,
Jake, Jack, Walter and Ruth**. It does not publish or enable a new mechanic.

## Finding

The original Android CE tuning has no romance transition out of **Good Friend**
or **Best Friend**. Increasing romance points cannot cross an absent transition.
Ordinary Friend does have that route. All five named NPCs use the same graph.
This is a concrete possible explanation if they are already Good/Best Friends;
no supplied save establishes their current status. A permanent ban on those five
characters has not been established.

| Current stage | Original outgoing rules | Proposed additional rule |
| --- | --- | --- |
| Acquaintance (1) | Friend at friendship ≥+5; Budding Romance at romance ≥+5; Disliked at friendship ≤−5 | None |
| Friend (5) | Good Friend at friendship ≥+15; Disliked at friendship ≤−10; Budding Romance at romance ≥+10 | None |
| Good Friend (6) | Friend at friendship ≤−10; Best Friend at friendship ≥+25 | Budding Romance at romance ≥+10 |
| Best Friend (7) | Good Friend at friendship ≤−15 | Budding Romance at romance ≥+10 |

Scores are accumulated 16.16 values within the current stage, not a permanently
increasing global affection total. The engine caps romance at +30; the original
Good/Best Friend graph still cannot advance at that maximum. State changes reset
both accumulated score channels. Existing branches have first-match priority.

## Named Sims

| Sim | Native NPC ID | Relevant finding |
| --- | ---: | --- |
| Luke | 11 | Shared graph; ordinary romance action conditions can match. |
| Jake | 6 | Shared graph; static pairing data links Jake and Maggie. |
| Jack | 2 | Shared graph; static pairing data links Jack and Jill. |
| Walter | 9 | Shared graph; traits select different action outcomes, not a blanket name rejection. |
| Ruth | 1 | Shared graph; ordinary romance action conditions can match. |

The paired-reference field is used by event/profile paths. It should be preserved;
this investigation does not redefine every pair as a marriage or delete existing
partners. Unresolved appearance/job columns were not relabeled as sex, age,
orientation or a romance-permission flag. No shared exclusion flag across these
five was found in the inspected data and action path.

## Original Android evidence

The fetched `flip3` HEAD was `223056b381001d422bab459cd9a5cc5cd37e3cc1`.
The inspected APK is the exact published 0.1.15/code115, SHA256
`a759fb156efb526149e3c0e3a9ca3bba4d5646aff4198ae8946dbc7947c7f5eb`.
Original decompressed S3E SHA256 is
`8198558b93316a963c2106f172fde53015063955af16d2aa13ee51a89a1e114a`.
Resource `res.dz` entry6, `simsdata.bin`, is22,030bytes, SHA256
`778c385d6ee62e48bacfea06d5a61b71d1caced5a68b45edaf3cfdb1801511f4`.
English names/labels come from entry15, not another language or Sims edition.

- Original loader `game+0xcf0bc` parses relationship/action constants. The original
  constructor/parser executed on the shipped data; unrelated delegated SimWorld
  consumers were modeled as no-ops. A separate raw parser matches all15 graph rows.
- Graph arrays in SimData are target states at `+0x3e0`, score-channel indices at
  `+0x3f4`, and signed-short thresholds at `+0x408`. The raw section begins at
  resource `+0x57d`; Good/Best Friend records begin `+0x5df`/`+0x5ef`.
- Resolver `game+0xce014` indexes the current state, compares the indicated
  accumulated channel with threshold shifted16, then calls `+0xce330` on the
  first satisfied rule. States6/7 lack any target8 rule in the original data.
- Action selector `+0xc8a34` considers conversation context, traits, state masks,
  history and other prerequisites. Acceptance gate `+0xc5cc4` reads bit14 of its
  selected condition flags. The inspected social-action path does not select a
  rejection merely because the NPC is one of the five named characters.
- Action effects `+0x5b4`/`+0x5c8` feed friendship/romance deltas to `+0xc7370`;
  the ordinary outcome path then calls the transition resolver. Flirt83 and
  Embrace86 have positive romance outcomes. Repetition and traits still matter.
- Normal setter `+0xce330` writes the existing relationship state, clears the
  two accumulated channels and performs the existing goal/notification work.
  Proposal, marriage, breakup and divorce use separate existing action paths.

REA instructions/provider guidance were read. No configured Hopper/Ghidra/IDA
provider was available; existing S3CE extraction, Capstone and Unicorn workflows
were reused for these narrow questions. There is no REA provider implementation
or claim of provider execution in this investigation.

## Feasible implementation

Append only two shared graph rules: `6→8` and `7→8`, channel1, threshold10.
Keep the existing rules ahead of them, preserving downgrade/promotion priority.
This reuses the ordinary Friend→Budding Romance threshold and normal setter.
It would let close friendships develop through ordinary romantic play, including
these five NPCs, without adding a new relationship state or rewriting saves.
Acceptance remains dependent on the existing action/context/trait rules.

A guarded change to the shipped tuning is a coherent implementation option. Its
resource/archive lengths and offsets must be rebuilt correctly; the builder's
asset-invariance checks must explicitly permit only this intended tuning change.
Alternatively a narrow runtime graph augmentation needs its own profile/ownership
checks. Do not bypass the action-acceptance gate globally or change NPC identities.

This is a proposal backed by instruction-level experiments, not a new APK.
Existing-save loading, actual Good/Best Friend→Budding Romance gameplay, later
Date/Partner/proposal progression, existing pair behavior, saving/reloading and
stable Hot Smooch execution remain release checks for an implementation.

## Validation and limits

- 936 original ARM selector executions use the extracted condition/trait tables,
  synthetic conversation/history/skill inputs and actual vector operations.
  Seventy-eight explicit assertions verify Flirt/Embrace select non-reject rows
  for all13 NPCs at Friend/Good/Best Friend in romantic conversation. An absent matching
  row is recorded as −1 and is never treated as automatic acceptance.
- 266 resolver runs compare original versus research-only additive graphs: all15
  states, low/high relocation mappings, all13 NPC IDs, the exact10-point boundary,
  and prior branch ordering. Zero failures;38 intended cases change and unrelated
  states keep their results. Vector copy/destruction and final setter/UI endpoints
  are modeled in this fixture.
- 10 separate original setter runs cover the five named NPCs from Good and Best
  Friend. They verify only the selected NPC changes to state8, both scores clear,
  and expected bookkeeping/notification endpoints are reached. UI/goal-award/scene
  boundaries remain modeled. These are not completed Android conversations.

No installed app, original APK, personal save or live game process was changed.
The user has not supplied the five current relationship statuses. A different
stage, rejected conversation, context or existing-partner behavior could require
additional diagnosis. See [sanitized receipt](relationship-research-evidence.json).

The portable read-only parser can reproduce the graph from the signed baseline:

```sh
python3 scripts/research_relationships.py --apk /path/to/S3CE-0.1.15-flip3-socials-arm32.apk
```

Historical [original iPhone player reports](https://chadaustin.me/2010/01/the-completionists-guide-to-sims-3-iphone/)
describe the same friendship obstacle and successful romance with some named
Sims. That mixed-platform page was an investigative lead; the Android data and
native instruction experiments above establish this proposal's technical basis.

The reproducible instruction-level analysis bundle is retained privately as
`S3CE-relationship-research-2026-11-15.zip` (60,891bytes, SHA256
`96d1ab49b9ad204a6b5cf25b48632f1afbe7a23a15f9464871bbe8ccee003390`).
It contains the scripts, recovery commands and full receipts for the936/266/10
experiments, without game binaries, assets, heap dumps, phone reports or saves.
