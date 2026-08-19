monitor.alsa.rules = [
  {
    matches = [
      {
        node.name = "alsa_output.usb-.*analog-stereo"
      }
    ]
    actions = {
      update-props = {
        device.form_factor = "headphones"
        device.icon_name = "audio-headphones"
      }
    }
  }
]
