# Architecture

Vaydeer Studio separates protocol frames, HID discovery, device adapters, the
read-only keepalive service, application models, and QML presentation. This
separation keeps UI features from bypassing the protocol safety gate.
