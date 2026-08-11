# A real X11 desktop session: display server, window manager and a GUI toolkit. This is a
# container, not a virtual machine; see PROTOCOL.md for why the distinction is kept.
FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
      xvfb x11-utils xdotool openbox python3-tk imagemagick \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /agent
