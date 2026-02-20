rule = {
  matches = {
    {
      { "media.class", "equals", "Audio/Sink" },
    },
  },
  apply_properties = {
    ["node.autoconnect"] = true,
    ["node.autoconnect-streams"] = true,
  },
}
