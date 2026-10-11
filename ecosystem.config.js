const path = require("path")

module.exports = {
    apps: [
        {
            name: "lenia-client",
            cwd: __dirname,
            script: ".venv/bin/lenia-client",
            interpreter: path.join(__dirname, ".venv/bin/python"),
            watch: false,
            min_uptime: 0,
            restart_delay: 3000,
            env: {
                XDG_RUNTIME_DIR: process.env.XDG_RUNTIME_DIR || `/run/user/${process.getuid()}`,
                WAYLAND_DISPLAY: process.env.WAYLAND_DISPLAY || "wayland-0",
                SDL_VIDEODRIVER: "wayland",
                PYTHONUNBUFFERED: "1",
            },
        },
    ],
}
