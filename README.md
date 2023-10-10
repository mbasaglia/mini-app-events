Event Telegram Mini-App Demo
============================

This app shows an interface that allows users to mark events they plan to attend.

User will receive a notification when the event is starting.

Live instance: [@GlaxMiniEventBot](https://t.me/GlaxMiniEventBot).

More info in the [Mini Event app page](./docs/apps/mini_event.md).

Full documentation is available on [Read the Docs](https://mini-apps.readthedocs.io/en/latest/).

## Limitations

The events app is a technical demo, for a fully functional app some changes are needed.

For one, the events are only specified as a time (not a date), this allows the bot
to always show some data regardless of the current date.

The bot will send notifications based on the server time, which might be different from the time shown to the users.


Set Up
------

See the [installation page](./docs/installation/basic.md) for installation and setup guide.


Mini Apps
---------

The installation guide above shows the configuration for the "Mini Events" app, which serves as a demo for the system.

You can find detailed description, configuration options, and limitations of all the availble apps in the
[Available Apps](./docs/apps/index.md) page.

To make your own mini app, see [Making Your Own App](./docs/apps/custom.md) page.


License
-------

GPLv3+ https://www.gnu.org/licenses/gpl-3.0.en.html
