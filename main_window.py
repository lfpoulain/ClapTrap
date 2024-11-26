from vban_sources_frame import VBANSourcesFrame
from vban_discovery import VBANDiscovery, VBANSource

# ...

# Section Sources VBAN
sources_frame = VBANSourcesFrame(self)
sources_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
sources_frame.set_discovery(self.vban_discovery)  # Assurez-vous que self.vban_discovery existe 