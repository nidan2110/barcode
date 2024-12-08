import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from barcode import Code128
from barcode.writer import ImageWriter
from PIL import Image, ImageTk
import zipfile
from io import BytesIO
from datetime import datetime
import logging

logging.basicConfig(filename='barcode_app.log', level=logging.DEBUG)


class BarcodeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Barcode Generator")
        
        # Set a minimalistic full screen window
        self.root.attributes("-fullscreen", True)

        # Initialize barcode count
        self.total_barcodes = 0
        self.barcodes = []
        self.max_barcodes_per_row = 5  # Number of barcodes per row

        # Fonts and styles for minimalistic UI
        heading_font = ("Helvetica", 32, "bold")  # Larger title font size
        label_font = ("Arial", 18)  # Increased label font size
        button_font = ("Arial", 14, "bold")  # Subtle button font size
        entry_font = ("Arial", 16)  # Increased text box font size
        bg_color = "#f4f4f9"  # Soft gray background for minimalistic look
        button_color = "#5C6BC0"  # Muted blue for button color

        # Title
        title_label = tk.Label(root, text="Barcode Generator", font=heading_font, bg=bg_color, fg="#333")
        title_label.pack(pady=40)

        # Input Frame
        input_frame = tk.Frame(root, bg=bg_color)
        input_frame.pack(pady=30)

        ttk.Label(input_frame, text="Guest Type:", font=label_font, background=bg_color).grid(row=0, column=0, padx=20, pady=15, sticky="w")
        self.guest_type_combobox = ttk.Combobox(input_frame, font=entry_font, width=40, state="readonly")
        self.guest_type_combobox["values"] = ["1 Guest with Room", "2 Guest without Room", "3 Swimming"]
        self.guest_type_combobox.grid(row=0, column=1, padx=20, pady=15)
        self.guest_type_combobox.set("1 Guest with Room")  # Default value

        ttk.Label(input_frame, text="Guest ID (Auto-Generated):", font=label_font, background=bg_color).grid(row=1, column=0, padx=20, pady=15, sticky="w")
        self.guest_id_label = ttk.Label(input_frame, text="Auto-Generated", font=entry_font, width=40)
        self.guest_id_label.grid(row=1, column=1, padx=20, pady=15)

        ttk.Label(input_frame, text="Guest Count:", font=label_font, background=bg_color).grid(row=2, column=0, padx=20, pady=15, sticky="w")
        self.guest_count_entry = ttk.Entry(input_frame, font=entry_font, width=40)
        self.guest_count_entry.grid(row=2, column=1, padx=20, pady=15)
        self.guest_count_entry.insert(0, "Enter Guest Count")
        self.guest_count_entry.bind("<FocusIn>", self.remove_placeholder_guest_count)

        # Room Number Entry (Only visible for "1 Guest with Room")
        ttk.Label(input_frame, text="Room Number (if applicable):", font=label_font, background=bg_color).grid(row=3, column=0, padx=20, pady=15, sticky="w")
        self.room_number_entry = ttk.Entry(input_frame, font=entry_font, width=40)
        self.room_number_entry.grid(row=3, column=1, padx=20, pady=15)
        self.room_number_entry.grid_forget()  # Initially hide

        # Bind the selection event for guest type to show room number input when necessary
        self.guest_type_combobox.bind("<<ComboboxSelected>>", self.update_guest_type)

        # Buttons (using minimalist design)
        button_frame = tk.Frame(root, bg=bg_color)
        button_frame.pack(pady=40)

        self.generate_button = tk.Button(button_frame, text="Generate Barcodes", font=button_font, bg=button_color, fg="white", command=self.generate_barcodes, height=2, width=20, relief="flat", bd=2)
        self.generate_button.grid(row=0, column=0, padx=20, pady=15)

        self.reset_button = tk.Button(button_frame, text="Reset", font=button_font, bg="#EF5350", fg="white", command=self.reset_fields, height=2, width=20, relief="flat", bd=2)
        self.reset_button.grid(row=0, column=1, padx=20, pady=15)

        self.download_button = tk.Button(button_frame, text="Download as ZIP", font=button_font, bg="#26A69A", fg="white", command=self.download_zip, height=2, width=20, relief="flat", bd=2)
        self.download_button.grid(row=0, column=2, padx=20, pady=15)

        # Total Barcodes Label
        self.total_label = tk.Label(root, text=f"Total Barcodes Generated: {self.total_barcodes}", font=("Arial", 18), bg=bg_color, fg="#333")
        self.total_label.pack(pady=20)

        # Scrollable Canvas for Barcode Preview
        preview_frame = tk.Frame(root, bg=bg_color)
        preview_frame.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(preview_frame, bg="white", height=500, bd=3, relief="flat", scrollregion=(0, 0, 5000, 0))
        self.scrollbar = ttk.Scrollbar(preview_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="white")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Close Button at the top right corner for a minimalist look
        self.root.after(100, self.position_close_button)

    def position_close_button(self):
        # Place the Close button at the top-right corner
        self.close_button = tk.Button(self.root, text="Close", font=("Arial", 14), bg="#EF5350", fg="white", command=self.root.quit, height=2, width=10, relief="flat", bd=2)
        self.close_button.place(x=self.root.winfo_width() - 120, y=10)

    def update_guest_type(self, event):
        guest_type = self.guest_type_combobox.get()
        if guest_type == "1 Guest with Room":
            self.room_number_entry.grid(row=3, column=1, padx=20, pady=15)
        else:
            self.room_number_entry.grid_forget()

    def generate_barcodes(self):
        guest_type = self.guest_type_combobox.get()
        guest_id = self.generate_guest_id(guest_type)
        guest_count = self.guest_count_entry.get().strip()
        current_date = datetime.now().strftime("%Y-%m-%d")

        if guest_id is None:
            messagebox.showerror("Error", "Please provide valid inputs!")
            return

        try:
            guest_count = int(guest_count)
            if guest_count <= 0:
                raise ValueError

            # Reset previous barcodes
            self.barcodes = []
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()

            # Generate and display barcodes
            for i in range(guest_count):
                barcode_data = f"{guest_id}-{i+1}-{current_date}"
                buffer = BytesIO()

                # Generate barcode and save it to buffer
                code = Code128(barcode_data, writer=ImageWriter())
                code.write(buffer)

                # Convert buffer to an image
                buffer.seek(0)
                img = Image.open(buffer)
                img = img.resize((200, 100))  # Slightly smaller for a minimal design
                photo = ImageTk.PhotoImage(img)

                # Calculate the row and column for wrapping
                row = i // self.max_barcodes_per_row
                column = i % self.max_barcodes_per_row

                # Display barcode in scrollable frame
                label = tk.Label(self.scrollable_frame, image=photo, bg="white")
                label.image = photo
                label.grid(row=row, column=column, padx=10, pady=10)  # Use grid layout for wrapping

                # Append barcode data to list for ZIP download
                self.barcodes.append((f"{guest_id}-{i+1}", buffer.getvalue()))

            self.total_barcodes += guest_count
            self.update_total_label()

            messagebox.showinfo("Success", f"{guest_count} barcodes generated successfully!")

        except ValueError:
            messagebox.showerror("Error", "Guest Count must be a positive number!")
            try:
                # Add logging to see where the issue occurs
                logging.debug("Generating barcodes...")
                # Your barcode generation logic
            except Exception as e:
                logging.error(f"Error generating barcode: {e}")

    def generate_guest_id(self, guest_type):
        guest_id = ""
        if guest_type == "1 Guest with Room":
            room_number = self.room_number_entry.get().strip()
            if not room_number.isdigit():
                messagebox.showerror("Error", "Please enter a valid room number!")
                return None
            guest_id = f"GR{room_number}"  # Example format for Guest with Room
        elif guest_type == "2 Guest without Room":
            guest_id = "GNR"  # Guest without Room
        elif guest_type == "3 Swimming":
            guest_id = "GSW"  # Swimming Guest
        return guest_id

    def reset_fields(self):
        self.guest_type_combobox.set("1 Guest with Room")
        self.guest_count_entry.delete(0, tk.END)
        self.guest_count_entry.insert(0, "Enter Guest Count")
        self.room_number_entry.delete(0, tk.END)
        self.room_number_entry.grid_forget()
        self.total_barcodes = 0
        self.update_total_label()
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

    def update_total_label(self):
        self.total_label.config(text=f"Total Barcodes Generated: {self.total_barcodes}")

    def download_zip(self):
        if not self.barcodes:
            messagebox.showerror("Error", "No barcodes generated yet!")
            return

        # Create a ZIP file
        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for barcode_id, barcode_data in self.barcodes:
                zipf.writestr(f"{barcode_id}.png", barcode_data)

        zip_buffer.seek(0)

        # Save ZIP file
        file_path = filedialog.asksaveasfilename(defaultextension=".zip", filetypes=[("ZIP files", "*.zip")])
        if file_path:
            with open(file_path, "wb") as f:
                f.write(zip_buffer.read())

            messagebox.showinfo("Success", "Barcodes downloaded successfully!")

    def remove_placeholder_guest_count(self, event):
        if self.guest_count_entry.get() == "Enter Guest Count":
            self.guest_count_entry.delete(0, tk.END)


if __name__ == "__main__":
    root = tk.Tk()
    app = BarcodeApp(root)
    root.mainloop()
