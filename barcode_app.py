import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from barcode import Code128
from barcode.writer import ImageWriter
from PIL import Image, ImageTk, ImageFont
import zipfile
from io import BytesIO
from datetime import datetime
import logging
import os

logging.basicConfig(filename='barcode_app.log', level=logging.DEBUG)

class BarcodeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Barcode Generator")
        self.root.attributes("-fullscreen", True)

        self.total_barcodes = 0
        self.barcodes = []
        self.max_barcodes_per_row = 5  # Number of barcodes per row

        # Fonts and styles
        heading_font = ("Helvetica", 32, "bold")
        label_font = ("Arial", 18)
        button_font = ("Arial", 14, "bold")
        entry_font = ("Arial", 16)
        bg_color = "#f4f4f9"
        button_color = "#5C6BC0"

        title_label = tk.Label(root, text="Barcode Generator", font=heading_font, bg=bg_color, fg="#333")
        title_label.pack(pady=40)

        input_frame = tk.Frame(root, bg=bg_color)
        input_frame.pack(pady=30)

        ttk.Label(input_frame, text="Guest Type:", font=label_font, background=bg_color).grid(row=0, column=0, padx=20, pady=15, sticky="w")
        self.guest_type_combobox = ttk.Combobox(input_frame, font=entry_font, width=40, state="readonly")
        self.guest_type_combobox["values"] = ["1. Regular", "2. Guest with Room", "3. Guest without Room", "4. Waterpark"]
        self.guest_type_combobox.grid(row=0, column=1, padx=20, pady=15)
        self.guest_type_combobox.set("1. Guest with Room")

        ttk.Label(input_frame, text="Guest ID (Auto-Generated):", font=label_font, background=bg_color).grid(row=1, column=0, padx=20, pady=15, sticky="w")
        self.guest_id_label = ttk.Label(input_frame, text="Auto-Generated", font=entry_font, width=40)
        self.guest_id_label.grid(row=1, column=1, padx=20, pady=15)

        ttk.Label(input_frame, text="Guest Count:", font=label_font, background=bg_color).grid(row=2, column=0, padx=20, pady=15, sticky="w")
        self.guest_count_entry = ttk.Entry(input_frame, font=entry_font, width=40)
        self.guest_count_entry.grid(row=2, column=1, padx=20, pady=15)
        self.guest_count_entry.insert(0, "Enter Guest Count")
        self.guest_count_entry.bind("<FocusIn>", self.remove_placeholder_guest_count)

        ttk.Label(input_frame, text="Room Number (if applicable):", font=label_font, background=bg_color).grid(row=3, column=0, padx=20, pady=15, sticky="w")
        self.room_number_entry = ttk.Entry(input_frame, font=entry_font, width=40)
        self.room_number_entry.grid(row=3, column=1, padx=20, pady=15)
        self.room_number_entry.grid_forget()

        self.guest_type_combobox.bind("<<ComboboxSelected>>", self.update_guest_type)

        button_frame = tk.Frame(root, bg=bg_color)
        button_frame.pack(pady=40)

        self.generate_button = tk.Button(button_frame, text="Generate Barcodes", font=button_font, bg=button_color, fg="white", command=self.generate_barcodes, height=2, width=20, relief="flat", bd=2)
        self.generate_button.grid(row=0, column=0, padx=20, pady=15)

        self.reset_button = tk.Button(button_frame, text="Reset", font=button_font, bg="#EF5350", fg="white", command=self.reset_fields, height=2, width=20, relief="flat", bd=2)
        self.reset_button.grid(row=0, column=1, padx=20, pady=15)

        self.download_button = tk.Button(button_frame, text="Download as ZIP", font=button_font, bg="#26A69A", fg="white", command=self.download_zip, height=2, width=20, relief="flat", bd=2)
        self.download_button.grid(row=0, column=2, padx=20, pady=15)

        self.print_button = tk.Button(button_frame, text="Print Barcode", font=button_font, bg="#FFA726", fg="white", command=self.print_barcode, height=2, width=20, relief="flat", bd=2)
        self.print_button.grid(row=0, column=3, padx=20, pady=15)

        self.total_label = tk.Label(root, text=f"Total Barcodes Generated: {self.total_barcodes}", font=("Arial", 18), bg=bg_color, fg="#333")
        self.total_label.pack(pady=20)

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

        self.root.after(100, self.position_close_button)

    def position_close_button(self):
        self.close_button = tk.Button(self.root, text="Close", font=("Arial", 14), bg="#EF5350", fg="white", command=self.root.quit, height=2, width=10, relief="flat", bd=2)
        self.close_button.place(x=self.root.winfo_width() - 120, y=10)

    def update_guest_type(self, event):
        guest_type = self.guest_type_combobox.get()
        if guest_type in ["1. Regular", "1. Guest with Room"]:
            self.room_number_entry.grid(row=3, column=1, padx=20, pady=15)
        else:
            self.room_number_entry.grid_forget()

    def generate_barcodes(self):
        guest_type = self.guest_type_combobox.get()
        guest_id = self.generate_guest_id(guest_type)
        guest_count = self.guest_count_entry.get().strip()
        current_date = datetime.now().strftime("%Y-%m-%d")
        room_number = self.room_number_entry.get().strip()

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
                if guest_type == "1. Guest with Room" and room_number:
                    barcode_data = f"{guest_id}-{room_number}-{i+1}-{current_date}"
                else:
                    barcode_data = f"{guest_id}-{i+1}-{current_date}"

                buffer = BytesIO()
                code = Code128(barcode_data, writer=ImageWriter(font=r'C:\Windows\Fonts\Arial\Arial-Black.ttf'))
                code.write(buffer)
                buffer.seek(0)
                image = Image.open(buffer)

                barcode_image = ImageTk.PhotoImage(image)
                self.barcodes.append(barcode_image)
                label = tk.Label(self.scrollable_frame, image=barcode_image, bd=5, relief="solid")
                label.pack(side="left", padx=10, pady=10)

                buffer.close()

            self.total_barcodes += guest_count
            self.total_label.config(text=f"Total Barcodes Generated: {self.total_barcodes}")

        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number for guest count!")

    def generate_guest_id(self, guest_type):
        if guest_type == "1. Regular":
            return f"REG-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        elif guest_type == "2. Guest with Room":
            return f"GR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        elif guest_type == "3. Guest without Room":
            return f"NR-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        elif guest_type == "4. Waterpark":
            return f"WP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        else:
            return None

    def download_zip(self):
        if not self.barcodes:
            messagebox.showinfo("Info", "No barcodes to download.")
            return

        zip_filename = filedialog.asksaveasfilename(defaultextension=".zip",
                                                     filetypes=[("ZIP files", "*.zip")])
        if zip_filename:
            with zipfile.ZipFile(zip_filename, 'w') as zipf:
                for i, barcode in enumerate(self.barcodes):
                    barcode_path = f"barcode_{i+1}.png"
                    barcode.write(barcode_path)  # Save as a temporary PNG file
                    zipf.write(barcode_path)
                    os.remove(barcode_path)  # Clean up after adding to ZIP
            messagebox.showinfo("Success", "Barcodes downloaded successfully!")

    def reset_fields(self):
        self.guest_type_combobox.set("1. Regular")
        self.guest_count_entry.delete(0, tk.END)
        self.guest_count_entry.insert(0, "Enter Guest Count")
        self.room_number_entry.delete(0, tk.END)
        self.barcodes = []
        self.total_barcodes = 0
        self.total_label.config(text=f"Total Barcodes Generated: {self.total_barcodes}")
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

    def print_barcode(self):
            if not self.barcodes:
                messagebox.showerror("Error", "No barcodes to print!")
                return

            # A4 dimensions in pixels (300 DPI resolution)
            a4_width, a4_height = 2480, 3508
            barcode_width, barcode_height = 600, 150  # Each barcode will be resized to 2x8 inches (300 DPI)
            vertical_spacing = 200  # Space between barcodes in pixels

            # Create a blank A4 canvas
            a4_canvas = Image.new("RGB", (a4_width, a4_height), "white")
            current_y = 50  # Start position for the first barcode

            for i, (filename, barcode_data) in enumerate(self.barcodes):
                # Load barcode image from data
                barcode_image = Image.open(BytesIO(barcode_data))
                barcode_image = barcode_image.resize((barcode_width, barcode_height))  # Resize to fit strip dimensions

                # Check if barcode fits on the current page
                if current_y + barcode_height > a4_height:
                    # Save current page and start a new one
                    a4_canvas.save(f"barcodes_page_{i // 20 + 1}.pdf")
                    a4_canvas = Image.new("RGB", (a4_width, a4_height), "white")
                    current_y = 50

                # Paste the barcode onto the A4 canvas
                a4_canvas.paste(barcode_image, (50, current_y))
                current_y += barcode_height + vertical_spacing

            # Save the final page
            if self.barcodes:
                guest_id = self.barcodes[0][0]  # Use the guest ID from the first barcode
                current_date = datetime.now().strftime("%Y%m%d")
                output_file = f"Barcodes_{guest_id}_{current_date}.pdf"
                a4_canvas.save(output_file)
            else:
                messagebox.showerror("Error", "No barcodes to save!")
                return


            # Inform the user and open the PDF
            messagebox.showinfo("Success", f"Barcodes saved as PDF: {output_file}")
            try:
                import os
                os.startfile(output_file)  # Open the file for printing
            except Exception as e:
                logging.error(f"Error opening file: {e}")
                messagebox.showerror("Error", f"Could not open the PDF: {e}")

    def remove_placeholder_guest_count(self, event):
        if self.guest_count_entry.get() == "Enter Guest Count":
            self.guest_count_entry.delete(0, tk.END)


        self.update_total_label()

if __name__ == "__main__":
    root = tk.Tk()
    app = BarcodeApp(root)
    root.mainloop()
