# openai_service.py
import os
import re
import json
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class OpenAIService:
    def __init__(self):
        """Initialize the OpenAI client with API key from environment"""
        api_key = os.environ.get("OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
            
        self.client = OpenAI(api_key=api_key)
    
    def detect_modules(self, syllabus_text):
        """Detect and extract modules/units from syllabus"""
        
        system_message = """
You are an expert curriculum analyzer. Your task is to identify and extract distinct modules, units, chapters, or topics from a syllabus.

Analyze the syllabus text and identify all modules/units/chapters. Return a structured JSON response with:
1. Module number/identifier
2. Module title/name
3. Brief description of module content
4. Key topics covered in that module

Format your response as a JSON array like this:
[
  {
    "module_id": "Module 1" or "Unit A" or "Chapter 1" (use the exact format from syllabus),
    "title": "Module title or name",
    "description": "Brief description of what this module covers",
    "topics": ["topic1", "topic2", "topic3"]
  }
]

If no clear modules are found, create logical groupings based on content themes.
Ensure each module has sufficient content to generate meaningful questions.
"""

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"Analyze this syllabus and extract modules:\n\n{syllabus_text[:3000]}"}
        ]

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Using stable model for reliability
                messages=messages,
                temperature=0.3,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            
            # Try to extract JSON from the response
            try:
                # Look for JSON array in the response
                json_start = content.find('[')
                json_end = content.rfind(']') + 1
                
                if json_start != -1 and json_end != -1:
                    json_str = content[json_start:json_end]
                    modules = json.loads(json_str)
                    return {
                        "success": True,
                        "modules": modules,
                        "error": None
                    }
            except:
                pass
            
            # Fallback: Parse text manually if JSON parsing fails
            modules = self._parse_modules_fallback(content)
            return {
                "success": True,
                "modules": modules,
                "error": None
            }
            
        except Exception as e:
            print(f"Module detection error: {e}")
            return {
                "success": False,
                "modules": [],
                "error": str(e)
            }
    
    def _parse_modules_fallback(self, content):
        """Fallback method to parse modules from text response"""
        modules = []
        lines = content.split('\n')
        current_module = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for module indicators
            if any(indicator in line.lower() for indicator in ['module', 'unit', 'chapter', 'topic']):
                if current_module:
                    modules.append(current_module)
                
                current_module = {
                    "module_id": line,
                    "title": line,
                    "description": "Module content analysis",
                    "topics": []
                }
            elif current_module and line.startswith('-'):
                current_module["topics"].append(line[1:].strip())
        
        if current_module:
            modules.append(current_module)
        
        # If no modules found, create a default one
        if not modules:
            modules = [{
                "module_id": "Module 1",
                "title": "Complete Syllabus",
                "description": "All syllabus content",
                "topics": ["General topics"]
            }]
        
        return modules
    
    def generate_module_questions(self, reference_text, syllabus_text, module_info, mcq_count, short_count, long_count, custom_instructions=""):
        """Generate questions for a specific module"""
        
        # Prepare module-specific system message
        system_message = f"""
You are an expert educator creating exam questions for a specific module/unit.

MODULE INFORMATION:
- Module: {module_info['module_id']}
- Title: {module_info['title']}
- Description: {module_info['description']}
- Key Topics: {', '.join(module_info['topics'])}

Generate EXACTLY:
- {mcq_count} multiple-choice questions (with 4 options and correct answer marked)
- {short_count} short answer questions  
- {long_count} long answer questions

IMPORTANT: 
- Focus ONLY on content related to this specific module
- Questions should directly relate to the module's topics and learning objectives
- Use the reference material but filter for content relevant to this module
- Ensure questions test understanding of module-specific concepts

{custom_instructions if custom_instructions else ""}

Format the output clearly with section headers:

MULTIPLE CHOICE QUESTIONS - {module_info['module_id']}:
Q1. [Question text related to {module_info['title']}]
A) Option A
B) Option B  
C) Option C
D) Option D
Answer: [Correct option]

SHORT ANSWER QUESTIONS - {module_info['module_id']}:
Q1. [Question text related to {module_info['title']}]

LONG ANSWER QUESTIONS - {module_info['module_id']}:
Q1. [Question text related to {module_info['title']}]
"""

        # Extract module-relevant content from reference text
        module_context = self._extract_module_context(reference_text, module_info)

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"MODULE SYLLABUS CONTENT: {syllabus_text[:1500]}"},
            {"role": "user", "content": f"RELEVANT REFERENCE MATERIAL: {module_context[:3000]}"}
        ]

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Using stable model
                messages=messages,
                temperature=0.7,
                max_tokens=3000
            )
            return {
                "success": True,
                "content": response.choices[0].message.content,
                "module_id": module_info['module_id'],
                "module_title": module_info['title'],
                "error": None
            }
        except Exception as e:
            print(f"Module question generation error: {e}")
            return {
                "success": False,
                "content": None,
                "module_id": module_info['module_id'],
                "module_title": module_info['title'],
                "error": str(e)
            }
    
    def _extract_module_context(self, reference_text, module_info):
        """Extract relevant portions of reference text for specific module"""
        module_keywords = []
        
        # Collect keywords from module info
        module_keywords.extend(module_info['topics'])
        module_keywords.append(module_info['title'])
        
        # Split reference text into chunks
        chunks = reference_text.split('\n\n')
        relevant_chunks = []
        
        for chunk in chunks:
            chunk_lower = chunk.lower()
            # Check if chunk contains module-relevant keywords
            for keyword in module_keywords:
                if keyword.lower() in chunk_lower:
                    relevant_chunks.append(chunk)
                    break
        
        # If we found relevant chunks, use them; otherwise use beginning of reference text
        if relevant_chunks:
            return '\n\n'.join(relevant_chunks[:10])  # Limit to first 10 relevant chunks
        else:
            return reference_text[:4000]  # Fallback to first part of reference
    
    def generate_questions(self, reference_text, syllabus_text, mcq_count, short_count, long_count, custom_instructions=""):
        """Generate questions using OpenAI API with better quota error handling"""
        
        # Prepare system message with instructions
        system_message = f"""
You are an expert educator who creates high-quality exam questions based on reference materials.

Generate exam questions as per the following requirements:

- {mcq_count} multiple-choice questions (with 4 options and correct answer marked)
- {short_count} short answer questions  
- {long_count} long answer questions

The questions should be based on the provided reference book content and aligned with the syllabus.

{custom_instructions if custom_instructions else ""}

Format the output clearly with appropriate section headers:

MULTIPLE CHOICE QUESTIONS:
Q1. [Question text]
A) Option A
B) Option B  
C) Option C
D) Option D
Answer: [Correct option]

SHORT ANSWER QUESTIONS:
Q1. [Question text]

LONG ANSWER QUESTIONS:
Q1. [Question text]
"""

        # Prepare the messages for the API call
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"SYLLABUS: {syllabus_text[:2000]}..."},
            {"role": "user", "content": f"REFERENCE MATERIAL: {reference_text[:4000]}..."}
        ]
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",  # Use cheaper model until quota is resolved
                messages=messages,
                temperature=0.7,
                max_tokens=3000  # Reduced to save costs
            )
            return {
                "success": True,
                "content": response.choices[0].message.content,
                "error": None
            }
        except Exception as e:
            error_message = str(e)
            
            # Handle specific quota errors with helpful messages
            if "429" in error_message or "insufficient_quota" in error_message:
                return {
                    "success": False,
                    "content": None,
                    "error": "OpenAI quota exceeded. Please add credits to your account at https://platform.openai.com/account/billing"
                }
            elif "401" in error_message:
                return {
                    "success": False,
                    "content": None,
                    "error": "Invalid API key. Please check your OpenAI API key configuration."
                }
            else:
                return {
                    "success": False,
                    "content": None,
                    "error": f"API Error: {error_message}"
                }
    
    def validate_api_key(self):
        """Test if the API key is valid"""
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            print(f"API key validation failed: {e}")
            return False
    
    def test_connection(self):
        """Test the OpenAI connection without using quota"""
        try:
            # This doesn't actually make an API call, just tests the client setup
            return self.client is not None
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
    
    def get_model_info(self):
        """Get information about available models"""
        try:
            models = self.client.models.list()
            return {
                "success": True,
                "models": [model.id for model in models.data],
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "models": [],
                "error": str(e)
            }
