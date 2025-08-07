# Exam Question Bank Generator

A web application that generates exam question banks using the ChatGPT API based on uploaded reference materials and syllabus.

## Features

- Upload reference books and syllabus (PDF format)
- Generate multiple-choice, short answer, and long answer questions
- Customizable number of questions for each type
- Custom instructions option for specialized requirements
- Progress tracking during generation
- Downloadable Excel output with organized question sections

## Technologies Used

- **Backend**: Python with Flask
- **Frontend**: Pure HTML/CSS/JavaScript (built from scratch)
- **AI**: OpenAI's ChatGPT API (GPT-4 or GPT-4o)
- **PDF Processing**: PyMuPDF
- **Excel Generation**: Pandas with Openpyxl

## Installation and Setup

### Prerequisites

- Python 3.8 or higher
- OpenAI API key

### Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/shrprem/AI Questionbank generator.git
   cd AI Questionbank generator
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your OpenAI API key:
   - Copy `.env.example` to `.env`
   - Add your OpenAI API key to the `.env` file
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

4. Run the application:
   ```bash
   python app.py
   ```

5. Access the application in your browser at `http://localhost:5000`

## Usage

1. Upload your reference book (PDF) and syllabus (PDF)
2. Specify how many questions you want of each type
3. Add any custom instructions (optional)
4. Click "Generate Questions"
5. Wait for processing (this may take a few minutes depending on file size)
6. Download the generated Excel file containing your questions

## Project Structure

- `app.py` - Main Flask application
- `templates/` - HTML templates
- `static/` - CSS, JavaScript, and other static assets
- `uploads/` - Temporary storage for uploaded PDFs
- `generated/` - Temporary storage for generated Excel files

## Error Handling

The application includes comprehensive error handling for:
- Invalid file types
- Missing files
- API failures
- Processing errors

## License

[MIT License](LICENSE)