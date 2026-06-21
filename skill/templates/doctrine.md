# OpenTSC Doctrine Template

Use this as `opentsc/_doctrine.md`.

## Value boundaries

- TODO(user): actions the system must never recommend.
- TODO(user): acceptable relationship costs.
- TODO(user): privacy/security requirements beyond local/offline defaults.

## Trust dimensions

Define only dimensions the user actually uses.

```yaml
trust_dimensions:
  delivery: "Can this person deliver promised work?"
  candor: "Will this person tell uncomfortable truth?"
```

## Suggestion quality dimensions

```yaml
suggestion_quality_dimensions:
  accuracy: "Did the prediction match reality?"
  usefulness: "Did the recommendation improve action?"
  reasoning_quality: "Was the reasoning chain inspectable and sound?"
comfort_feedback:
  record: true
  use_for_generation_tuning: false
```

## Relationship weights

```yaml
relationship_weights:
  affiliated: TODO(user)
  cooperative: TODO(user)
  friend: TODO(user)
  neutral: TODO(user)
  adversarial: TODO(user)
```

## Capability aggregation rules

- TODO(user): when to count another person's skill as mobilizable.
- TODO(user): what relationship costs are too high.
- TODO(user): review interval for mobilization confidence.
