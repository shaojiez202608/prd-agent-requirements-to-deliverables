# 06 Panel interaction specification

Templates: `panel-spec.template.md` and `panel-preview.template.html`.

The panel spec answers "is it usable", not "is it pretty":
1. Control to thing model mapping table (Control, Identifier, ID, Access, Interaction) between the dp-table markers.
2. Layout order of cards.
3. Control states: reported, pending, failed, offline. Writable controls show the new value only after the device
   reports it (command/report loop).
4. App interaction flow: sign in, add device (provisioning), device list, open panel, change a value, offline.
5. Per-control behaviour.

The preview HTML is the panel sketch. Every card carries `data-dp-id`, `data-dp-identifier`, `data-dp-access` and a
visible badge `ID n | identifier | access`, so reviewers see the ID on the sketch and the validator can read it.
