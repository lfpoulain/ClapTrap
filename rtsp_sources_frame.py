import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
from utils.settings_manager import settings

class RTSPSourcesFrame(ctk.CTkFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        # RTSP Sources Section
        rtsp_label = ctk.CTkLabel(self, text="RTSP Sources", font=("", 20))
        rtsp_label.pack(pady=10)

        # Form Frame
        form_frame = ctk.CTkFrame(self)
        form_frame.pack(fill="x", padx=20, pady=5)

        # Name input
        name_label = ctk.CTkLabel(form_frame, text="Name:")
        name_label.grid(row=0, column=0, padx=5, pady=5)
        self.name_entry = ctk.CTkEntry(form_frame)
        self.name_entry.grid(row=0, column=1, padx=5, pady=5)

        # URL input
        url_label = ctk.CTkLabel(form_frame, text="URL:")
        url_label.grid(row=1, column=0, padx=5, pady=5)
        self.url_entry = ctk.CTkEntry(form_frame)
        self.url_entry.grid(row=1, column=1, padx=5, pady=5)

        # Webhook URL input
        webhook_label = ctk.CTkLabel(form_frame, text="Webhook URL:")
        webhook_label.grid(row=2, column=0, padx=5, pady=5)
        self.webhook_entry = ctk.CTkEntry(form_frame)
        self.webhook_entry.grid(row=2, column=1, padx=5, pady=5)

        # Add button
        add_button = ctk.CTkButton(form_frame, text="Add RTSP Source", command=self.add_rtsp_source)
        add_button.grid(row=3, column=0, columnspan=2, pady=10)

        # Sources list frame
        self.sources_frame = ctk.CTkFrame(self)
        self.sources_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Load existing sources
        self.load_rtsp_sources()

    def create_source_frame(self, source):
        frame = ctk.CTkFrame(self.sources_frame)
        frame.pack(fill="x", padx=5, pady=2)

        # Source info
        info_text = f"{source['name']} - {source['url']}"
        if source.get('webhook_url'):
            info_text += f"\nWebhook: {source['webhook_url']}"
        
        info_label = ctk.CTkLabel(frame, text=info_text)
        info_label.pack(side="left", padx=5)

        # Enable/Disable switch
        switch_var = tk.BooleanVar(value=source.get('enabled', False))
        switch = ctk.CTkSwitch(frame, text="", variable=switch_var, 
                             command=lambda: self.toggle_source(source, switch_var))
        switch.pack(side="right", padx=5)

        # Delete button
        delete_btn = ctk.CTkButton(frame, text="Delete", 
                                 command=lambda: self.delete_source(source, frame))
        delete_btn.pack(side="right", padx=5)

    def add_rtsp_source(self):
        source = {
            "name": self.name_entry.get(),
            "url": self.url_entry.get(),
            "webhook_url": self.webhook_entry.get(),
            "enabled": True
        }
        
        if not source["name"] or not source["url"]:
            return
        
        settings.get()["rtsp_sources"].append(source)
        settings.save()
        
        self.create_source_frame(source)
        
        # Clear entries
        self.name_entry.delete(0, 'end')
        self.url_entry.delete(0, 'end')
        self.webhook_entry.delete(0, 'end')

    def load_rtsp_sources(self):
        for widget in self.sources_frame.winfo_children():
            widget.destroy()
            
        for source in settings.get()["rtsp_sources"]:
            self.create_source_frame(source)

    def toggle_source(self, source, switch_var):
        source["enabled"] = switch_var.get()
        settings.save()

    def delete_source(self, source, frame):
        settings.get()["rtsp_sources"].remove(source)
        settings.save()
        frame.destroy() 