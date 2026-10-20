# Open questions

Business facts that were not available. Nothing below was guessed in code or documents.

1. **Effect data.** The repository has no measured data on usage, cycle time or rework (only an unmeasured target
   exists). The repository makes no effect claim. Decide whether measured data will ever be published.
2. **Permission to publish the approach.** Whether the origin of this approach agrees to an abstracted public
   version has to be confirmed before publishing.
3. **Publishing channel and its tier.** Which content programme and which tier this repository goes to is not decided.
4. **Copyright holder in LICENSE.** `LICENSE` contains `<COPYRIGHT_HOLDER>`. Set it according to the publishing
   organisation's open-source rules.
5. **Security contact.** SECURITY.md points to the host platform's private reporting feature. Confirm the official
   contact channel for the final publishing location.
6. **Structured property type.** Is a struct or array data type needed in the thing model (for example timer lists),
   or does the target platform expect encoded strings? The current version uses `string` and records the encoding as
   an open item.
7. **Message format in the quick-start guide.** The command and report bodies are illustrative and vendor-neutral.
   If a specific platform is targeted later, its official message format needs to be used and verified.
8. **Language of deliverables.** Do the real consumers need Chinese deliverables, including the PDF? That needs a
   reviewed Unicode font.
9. **Frontline vs PM field split.** The split of fields between the two forms follows the spec's description of
   roles. It should be confirmed with real users.
