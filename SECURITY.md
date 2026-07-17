# Security Policy

The latest `1.x` release receives safety and security fixes. Development
snapshots and older `0.1.x` builds are not supported after the 1.0 release.

Report a vulnerability privately through [GitHub Security Advisories](https://github.com/callum-baillie/vaydeer-studio-linux/security/advisories/new),
especially if it could:

- emit an unknown command or firmware command `0xFC`;
- write keypad configuration without review and explicit confirmation;
- execute a Linux action outside its saved argument or shell policy;
- expose unsanitized diagnostics, local files, or profile secrets;
- bypass capability, backup, or read-back verification checks.

Do not include vendor firmware, USB serial numbers, private profiles, or raw
host logs in a public issue. For an ordinary non-sensitive defect, use the
public bug template with a sanitized diagnostics summary.

Vaydeer Studio is an unofficial community project. Reports sent to Vaydeer are
not automatically forwarded to this project.
