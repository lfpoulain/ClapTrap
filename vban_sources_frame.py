import tkinter as tk
from tkinter import ttk
from typing import Optional

from vban_discovery import VBANDiscovery, VBANSource

class VBANSourcesFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.discovery: Optional[VBANDiscovery] = None
        self._create_widgets()
        
    def _create_widgets(self):
        # Création d'un cadre avec bordure
        self.frame = ttk.LabelFrame(self, text="📹 Sources VBAN")
        self.frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Listbox pour afficher les sources
        self.sources_listbox = tk.Listbox(self.frame, height=6, width=40)
        self.sources_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Bouton de rafraîchissement
        refresh_btn = ttk.Button(
            self.frame, 
            text="Rafraîchir", 
            command=self.refresh_sources
        )
        refresh_btn.pack(pady=(0, 5))
        
        # Rafraîchissement initial
        self.after(1000, self.refresh_sources)
        
    def set_discovery(self, discovery: VBANDiscovery):
        """Configure l'instance de VBANDiscovery à utiliser"""
        self.discovery = discovery
        self.refresh_sources()
        
    def refresh_sources(self):
        """Rafraîchit la liste des sources VBAN"""
        if not self.discovery:
            self.sources_listbox.delete(0, tk.END)
            self.sources_listbox.insert(tk.END, "Service VBAN non initialisé")
            return
            
        # Efface la liste actuelle
        self.sources_listbox.delete(0, tk.END)
        
        # Récupère et affiche les sources actives
        sources = self.discovery.get_active_sources()
        if not sources:
            self.sources_listbox.insert(tk.END, "En attente de sources...")
            return
            
        for source in sources:
            self.sources_listbox.insert(
                tk.END, 
                f"{source.stream_name} ({source.ip}:{source.port})"
            ) 