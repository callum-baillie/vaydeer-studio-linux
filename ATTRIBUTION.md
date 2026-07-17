# Attribution and Licensing

Vaydeer Studio is an original implementation released under the MIT License.
It is an unofficial community project and is not affiliated with, endorsed by,
or supported by Vaydeer. Product names and trademarks remain the property of
their respective owners.

It does not include code, firmware, installers, extracted Electron assets, or
binary data from Vaydeer or the projects listed below.

| Source | Author / owner | Revision reviewed | License observed | Use in this project |
| --- | --- | --- | --- | --- |
| [vaydeer-macro-keyboard](https://github.com/philipp-fischer/vaydeer-macro-keyboard) | Philipp Fischer | `8fcc862029faefc99da506cdea1d722aa7af6894` | No license file found at review | Behavioral and packet-format reference only; no code reused. Its firmware flashing scope is deliberately excluded. |
| [go-vaydeer-ninepad-hid](https://github.com/alex-savin/go-vaydeer-ninepad-hid) | Alex Savin | `59512912b09f0df09ed75e5872c915e7dfcbab9d` | MIT | Protocol facts, interface roles, and async-event observations were independently reimplemented. No source files were copied. |
| [vaydeer-linux](https://github.com/grfrost/vaydeer-linux) | grfrost | `a8f4a93a9ba45aec5ea8c4f16ebf8d5c3df48b7d` | No license file found at review | Historical evidence that holding an HID interface open enables Linux operation; no code reused. |
| [Vaydeer-Keypad-Linux](https://github.com/TwinBlackbirds/Vaydeer-Keypad-Linux) | TwinBlackbirds | `fec08706b9a4bc66d9c329f45c9f8e60ce631340` | No license file found at review | Historical workaround reference only; no code reused. |
| [Vaydeer 9 Key Linux Fix](https://primis.org/blog/post/2024-06-17/Vaydeer-9-Key-Linux-Fix) | Primis | Retrieved 2026-07-15 | Web article | Historical workaround reference only. |
| Vaydeer downloads and firmware metadata | Vaydeer | Retrieved 2026-07-15 | Proprietary material; no binaries included | Public URLs and version metadata are documented only. |

The no-license sources are intentionally not a code source for this repository.
Protocol interoperability facts are not copied expression. The project’s own
research notes identify uncertainty rather than treating reverse-engineered
payload formats as stable.
