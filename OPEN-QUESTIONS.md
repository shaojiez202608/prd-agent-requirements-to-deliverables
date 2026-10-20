# Open questions

Technical and business facts that were not available. Nothing below was guessed in code or documents.

1. **Structured property type.** Is a struct or array data type needed in the thing model (for example timer lists),
   or does the target platform expect encoded strings? The current version uses `string` and records the encoding as
   an open item.
2. **Message format in the quick-start guide.** The command and report bodies are illustrative and vendor-neutral.
   If a specific platform is targeted later, its official message format needs to be used and verified.
3. **Language of deliverables.** Do the real consumers need Chinese deliverables, including the PDF? That needs a
   reviewed Unicode font. Until then, fields that reach the PDF are limited to Latin-1 (see DECISIONS.md D-25).
4. **Frontline vs PM field split.** The split of fields between the two forms follows the role description in the
   requirements input. It should be confirmed with real users.
5. **Enum encoding on the wire.** The quick-start examples send enum values as strings. If the target platform
   transmits enums by index, the order of `values` becomes part of the contract. `diff-model` already treats a
   reordering as breaking (D-29).
6. **Code owner.** `.github/CODEOWNERS` uses `@<MAINTAINER_GITHUB_HANDLE>`. Who owns CI, scanner configuration, AI
   configuration and the project rules once the repository is hosted?

