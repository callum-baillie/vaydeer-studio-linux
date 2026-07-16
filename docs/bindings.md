# Linux-side Bindings

Linux-side bindings represent actions that should not be put in vendor firmware:
application launches, URLs, files/directories, software-assisted text, scripts,
and complex behavior. The user service maintains the vendor event handle only
while a device is present and can use that same handle when event listening is
enabled.

Bindings store a target and an argument array. Command launch uses `subprocess`
without a shell by default. A future shell mode must be explicit in the profile
schema and UI. Bindings declare their trigger shape (`press`, `release`,
`hold`, `double_tap`, or `chord`); press/release dispatch is implemented now,
while timing/chord recognition remains a documented follow-up.
