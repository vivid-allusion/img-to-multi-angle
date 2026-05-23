# Python File Size Management Guidelines

## Objective
Maintain codebase readability and maintainability by preventing Python files from becoming unmanageably large.

## File Size Limits

### Soft Limit: 250 Lines
- When approaching 250 lines, provide justification for why additional length is necessary
- Examples of valid justifications:
  - Single cohesive class with many simple methods
  - Comprehensive API client for one service
  - Domain-specific data structures and related utilities

### Hard Limit: 400 Lines
- **No Python file should exceed 400 lines without explicit approval**
- When hitting this limit, immediately split the file into logical modules
- Exception: Configuration files, data files, and auto-generated code

## Automatic Splitting Rules

When a file exceeds limits, apply these rules in order:

1. **Multiple Classes**: Split each class into its own file
2. **Classes + Functions**: Separate classes from standalone functions
3. **Many Functions**: Group related functions into logical modules
4. **Single Large Class**: Extract helper methods into utility modules

## Structural Guidelines

### Preferred File Organization
- **One primary class per file** (plus small helper classes if tightly coupled)
- **Related utility functions** grouped in dedicated modules
- **Test files** may extend to 600 lines (different nature/purpose)

### Splitting Triggers (Regardless of Line Count)
- More than 3 classes in one file → split into separate files
- More than 15 top-level functions → group into logical modules
- Mixed responsibilities evident → separate by concern

## Implementation Process

### When Splitting Files:
1. **Identify logical boundaries** (related classes, function groups, responsibilities)
2. **Move most independent pieces first** (fewer import dependencies)
3. **Update imports** in all affected files
4. **Maintain existing public APIs** when possible
5. **Use clear, descriptive filenames** that reflect the module's purpose

### File Naming After Splits:
- `user_management.py` → `user.py` + `user_permissions.py`
- `data_processing.py` → `data_validator.py` + `data_transformer.py`
- `api_client.py` → `api_client.py` + `api_models.py` + `api_exceptions.py`

## Exceptions Requiring Approval

- **Domain-specific objects** that lose coherence when split
- **Generated code** (protobuf, API schemas, etc.)
- **Large but simple data structures** (mappings, configurations)
- **Framework requirements** that mandate specific file structures

## Monitoring and Compliance

- **Check file sizes** before committing any changes
- **Flag files** approaching 250 lines for review
- **Automatically reject** commits with files over 400 lines (unless pre-approved)
- **Document exceptions** with clear reasoning in commit messages

## Questions or Edge Cases

When uncertain about splitting decisions:
1. Favor **readability** over strict line counts
2. Prioritize **logical cohesion** over arbitrary boundaries
3. Consider **future maintenance** - will this split make debugging easier or harder?
4. Default to **smaller, focused modules** rather than large, multi-purpose files

---
*These guidelines prioritize long-term codebase maintainability while providing clear, measurable standards for automated enforcement.*