# 🛡️ Developer Command Vault v2

A professional, AI-powered desktop application for developers to store, manage, and share their most-used commands and snippets. Built with Python and Tkinter, featuring a modern hierarchical organization, interactive AI assistance, and high-quality document generation.

## ✨ Key Features

- **📂 Modern Hierarchy:** Organise commands into unlimited nested categories and subcategories.
- **🖱️ Drag & Drop:** Effortlessly restructure your vault by dragging categories to move them between root and subcategory positions.
- **🤖 Multi-Provider AI:** Integrated chat supporting Google Gemini, OpenAI, Groq, Mistral, and Local Ollama. Save AI-generated solutions directly to your vault.
- **📄 Professional PDF Export:** Generate beautiful, modern reports with syntax-styled code blocks, perfect internal alignment, and consistent margins.
- **📱 WhatsApp Integration:** Save your WhatsApp number and share command previews with a single click.
- **⚙️ Data Management:** A unified, perfectly aligned interface for importing and exporting JSON, CSV, Text, and PDF data.
- **🌱 Smart Import:** Support for hierarchical JSON imports using the `Parent > Child` syntax.
- **🖱️ Smooth Navigation:** Full mouse wheel support for categories, command lists, and AI chat.
- **🔒 API Locker:** Secure local management of AI provider keys and custom connection URLs.

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- (Linux users) `python3-tk` package for the graphical interface.

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/LalitGeek/command-vault.git
   cd command-vault
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application:**
   ```bash
   python command_vault.py
   ```

## 📖 Advanced Usage

### Category Management
- **Add:** Use the sidebar **+ Add** button to create root or subcategories.
- **Rename:** Open any category and click **✏️ Rename** in the header.
- **Reorganize:** Simply drag and drop categories in the sidebar. The system prevents invalid moves (like moving a parent into its own child).
- **Clear:** Use **🗑️ All** to permanently wipe the vault and reset it to a blank slate.

### Intelligent Imports
Use the **⚙️ Data Management** tab or the **📥 Import JSON** button to seed your vault. To import hierarchies, use the `>` separator:
```json
{
  "category": "Backend > Python > Django",
  "title": "Run Server",
  "command": "python manage.py runserver"
}
```

### Beautiful Exports
Export from the **Data Management** tab for bulk tasks, or use the **📄 PDF** and **📋 JSON** buttons inside any category for targeted exports. The PDF engine uses modern styling with `reportlab` to ensure a clean, professional look.

## 🛠️ Built With

- **Python** - Application Core
- **Tkinter** - GUI Framework
- **SQLite3** - Persistent Local Storage
- **ReportLab** - Modern PDF Generation Engine
- **Requests** - AI API Communication

## 👤 Author

**LalitGeek**

---
*Empowering developers to build their own private, high-performance command repository.*
