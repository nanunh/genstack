# PDF Merger Application

A simple web application to upload and merge multiple PDF files into a single PDF document.

## Features

- 📤 Upload multiple PDF files
- 🔄 Drag and drop support
- 📋 File list management
- 🔗 Merge PDFs in order
- 💾 Download merged PDF
- 🎨 Modern, responsive UI
- ⚡ Fast processing
- 🔒 Secure file handling

## Technology Stack

- **Frontend**: HTML, CSS, JavaScript
- **Backend**: Python Flask
- **PDF Processing**: PyPDF2

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Setup Steps

1. **Clone or download the project**

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python app.py
   ```

4. **Open your browser**
   ```
   http://localhost:5000
   ```

## Usage

1. **Upload PDFs**: Click "Browse Files" or drag and drop PDF files
2. **Review Files**: Check the list of uploaded files
3. **Merge**: Click "Merge PDFs" button
4. **Download**: Download your merged PDF file

## File Structure

```
pdf-merger-app/
├── app.py                 # Flask backend server
├── requirements.txt       # Python dependencies
├── static/
│   ├── index.html        # Main HTML page
│   ├── styles.css        # CSS styling
│   └── script.js         # JavaScript functionality
├── uploads/              # Temporary upload folder (auto-created)
└── merged/               # Merged PDFs folder (auto-created)
```

## API Endpoints

### Upload Files
- **POST** `/api/upload`
- Upload multiple PDF files
- Returns session ID

### Merge PDFs
- **POST** `/api/merge`
- Merge uploaded PDFs
- Returns download URL

### Download File
- **GET** `/api/download/<filename>`
- Download merged PDF

### Cleanup Session
- **DELETE** `/api/cleanup/<session_id>`
- Remove temporary files

## Configuration

- **Max File Size**: 50MB per file
- **Allowed Format**: PDF only
- **Port**: 5000 (default)

## Security Features

- File type validation
- File size limits
- Secure filename handling
- Session-based file isolation
- Automatic cleanup

## Browser Support

- Chrome (recommended)
- Firefox
- Safari
- Edge

## Troubleshooting

### Port already in use
```bash
# Change port in app.py
app.run(debug=True, host='0.0.0.0', port=5001)
```

### Module not found
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Upload fails
- Check file size (max 50MB)
- Ensure file is valid PDF
- Check disk space

## Development

### Run in development mode
```bash
python app.py
```

### Run in production
```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## License

MIT License - feel free to use for personal or commercial projects

## Support

For issues or questions, please create an issue in the repository.

## Future Enhancements

- [ ] PDF preview before merge
- [ ] Reorder files before merging
- [ ] Add page numbers
- [ ] Compress merged PDF
- [ ] Password protection
- [ ] Cloud storage integration

---

**Made with ❤️ using HTML, CSS, JavaScript, and Python Flask**