"""
Input validation and sanitization module for security and data integrity.
"""
import re
import os
import uuid
from typing import Optional, Tuple, List
from datetime import datetime


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class Validators:
    """Collection of input validators and sanitizers."""
    
    # Regex patterns
    PHONE_PATTERN = re.compile(r'^[6-9]\d{9}$')  # Indian mobile numbers
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    AADHAAR_PATTERN = re.compile(r'^\d{12}$')
    NAME_PATTERN = re.compile(r'^[a-zA-Z\s\-\.]+$')
    ALPHA_NUMERIC = re.compile(r'^[a-zA-Z0-9\s\-\.]+$')
    
    # Dangerous patterns for injection prevention
    SQL_INJECTION_PATTERN = re.compile(
        r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|EXEC|ALTER)\b|--|;|\/\*|\*\/)',
        re.IGNORECASE
    )
    XSS_PATTERN = re.compile(
        r'<script.*?>.*?<\/script>|javascript:|on\w+\s*=',
        re.IGNORECASE
    )
    
    # File validation
    ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/jpg'}
    ALLOWED_VIDEO_TYPES = {'video/mp4', 'video/quicktime', 'video/x-msvideo'}
    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_VIDEO_SIZE = 100 * 1024 * 1024  # 100MB
    
    @staticmethod
    def sanitize_string(input_string: str, max_length: int = None) -> str:
        """
        Sanitize string input to prevent injection attacks.
        
        Args:
            input_string: Raw input string
            max_length: Maximum allowed length
            
        Returns:
            Sanitized string
            
        Raises:
            ValidationError: If input contains dangerous patterns
        """
        if not input_string:
            return ""
        
        # Check for SQL injection patterns
        if Validators.SQL_INJECTION_PATTERN.search(input_string):
            raise ValidationError("Input contains potentially dangerous characters")
        
        # Check for XSS patterns
        if Validators.XSS_PATTERN.search(input_string):
            raise ValidationError("Input contains potentially dangerous content")
        
        # Trim whitespace
        sanitized = input_string.strip()
        
        # Apply length limit
        if max_length and len(sanitized) > max_length:
            raise ValidationError(f"Input exceeds maximum length of {max_length}")
        
        return sanitized
    
    @staticmethod
    def validate_name(name: str, field_name: str = "Name") -> str:
        """
        Validate person name.
        
        Args:
            name: Name to validate
            field_name: Field name for error messages
            
        Returns:
            Sanitized name
            
        Raises:
            ValidationError: If name is invalid
        """
        if not name or not name.strip():
            raise ValidationError(f"{field_name} is required")
        
        sanitized = Validators.sanitize_string(name, max_length=128)
        
        if not Validators.NAME_PATTERN.match(sanitized):
            raise ValidationError(f"{field_name} should only contain letters, spaces, hyphens, and dots")
        
        return sanitized
    
    @staticmethod
    def validate_phone_number(phone: str, field_name: str = "Phone Number") -> str:
        """
        Validate Indian phone number.
        
        Args:
            phone: Phone number to validate
            field_name: Field name for error messages
            
        Returns:
            Sanitized phone number
            
        Raises:
            ValidationError: If phone number is invalid
        """
        if not phone or not phone.strip():
            raise ValidationError(f"{field_name} is required")
        
        sanitized = Validators.sanitize_string(phone, max_length=10)
        
        if not Validators.PHONE_PATTERN.match(sanitized):
            raise ValidationError(f"{field_name} must be a valid 10-digit Indian mobile number")
        
        return sanitized
    
    @staticmethod
    def validate_email(email: str, required: bool = False) -> Optional[str]:
        """
        Validate email address.
        
        Args:
            email: Email to validate
            required: Whether email is required
            
        Returns:
            Sanitized email or None if not required and empty
            
        Raises:
            ValidationError: If email is invalid when provided
        """
        if not email or not email.strip():
            if required:
                raise ValidationError("Email is required")
            return None
        
        sanitized = Validators.sanitize_string(email, max_length=128)
        
        if not Validators.EMAIL_PATTERN.match(sanitized):
            raise ValidationError("Please provide a valid email address")
        
        return sanitized
    
    @staticmethod
    def validate_aadhaar(aadhaar: str, required: bool = False) -> Optional[str]:
        """
        Validate Aadhaar number.
        
        Args:
            aadhaar: Aadhaar number to validate
            required: Whether Aadhaar is required
            
        Returns:
            Sanitized Aadhaar or None if not required and empty
            
        Raises:
            ValidationError: If Aadhaar is invalid when provided
        """
        if not aadhaar or not aadhaar.strip():
            if required:
                raise ValidationError("Aadhaar number is required")
            return None
        
        sanitized = Validators.sanitize_string(aadhaar, max_length=12)
        
        if not Validators.AADHAAR_PATTERN.match(sanitized):
            raise ValidationError("Aadhaar number must be exactly 12 digits")
        
        return sanitized
    
    @staticmethod
    def validate_age(age: int) -> str:
        """
        Validate age.
        
        Args:
            age: Age to validate
            
        Returns:
            Age as string
            
        Raises:
            ValidationError: If age is invalid
        """
        if not isinstance(age, int) or age < 1 or age > 120:
            raise ValidationError("Age must be between 1 and 120")
        
        return str(age)
    
    @staticmethod
    def validate_address(address: str, max_length: int = 512) -> str:
        """
        Validate address.
        
        Args:
            address: Address to validate
            max_length: Maximum allowed length
            
        Returns:
            Sanitized address
            
        Raises:
            ValidationError: If address is invalid
        """
        if not address or not address.strip():
            raise ValidationError("Address is required")
        
        return Validators.sanitize_string(address, max_length=max_length)
    
    @staticmethod
    def validate_city(city: str, required: bool = False) -> Optional[str]:
        """
        Validate city name.
        
        Args:
            city: City to validate
            required: Whether city is required
            
        Returns:
            Sanitized city or None if not required and empty
            
        Raises:
            ValidationError: If city is invalid when provided
        """
        if not city or not city.strip():
            if required:
                raise ValidationError("City is required")
            return None
        
        sanitized = Validators.sanitize_string(city, max_length=64)
        
        if not Validators.NAME_PATTERN.match(sanitized):
            raise ValidationError("City should only contain letters, spaces, hyphens, and dots")
        
        return sanitized
    
    @staticmethod
    def validate_description(description: str, max_length: int = 1024) -> Optional[str]:
        """
        Validate description/text field.
        
        Args:
            description: Description to validate
            max_length: Maximum allowed length
            
        Returns:
            Sanitized description or None if empty
            
        Raises:
            ValidationError: If description is invalid
        """
        if not description or not description.strip():
            return None
        
        return Validators.sanitize_string(description, max_length=max_length)
    
    @staticmethod
    def validate_file_upload(
        file_obj, 
        allowed_types: set, 
        max_size: int,
        file_purpose: str = "file"
    ) -> Tuple[str, str]:
        """
        Validate file upload.
        
        Args:
            file_obj: Streamlit file upload object
            allowed_types: Set of allowed MIME types
            max_size: Maximum file size in bytes
            file_purpose: Description of file purpose for error messages
            
        Returns:
            Tuple of (file_path, unique_id)
            
        Raises:
            ValidationError: If file is invalid
        """
        if not file_obj:
            raise ValidationError(f"{file_purpose} is required")
        
        # Check file size
        if file_obj.size > max_size:
            size_mb = max_size / (1024 * 1024)
            raise ValidationError(f"{file_purpose} must be smaller than {size_mb:.0f}MB")
        
        # Check file type
        file_type = file_obj.type
        if file_type not in allowed_types:
            allowed_str = ", ".join(allowed_types)
            raise ValidationError(f"{file_purpose} must be one of: {allowed_str}")
        
        # Generate safe filename
        unique_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file_obj.name)[1]
        safe_filename = f"{unique_id}{file_extension}"
        
        # Ensure resources directory exists
        resources_dir = "./resources"
        if not os.path.exists(resources_dir):
            os.makedirs(resources_dir, exist_ok=True)
        
        file_path = os.path.join(resources_dir, safe_filename)
        
        return file_path, unique_id
    
    @staticmethod
    def validate_id_string(id_string: str) -> str:
        """
        Validate ID string (UUID format).
        
        Args:
            id_string: ID string to validate
            
        Returns:
            Validated ID string
            
        Raises:
            ValidationError: If ID is invalid
        """
        if not id_string or not id_string.strip():
            raise ValidationError("ID is required")
        
        try:
            # Try to parse as UUID
            uuid.UUID(id_string.strip())
            return id_string.strip()
        except ValueError:
            raise ValidationError("Invalid ID format")
    
    @staticmethod
    def validate_location(location: str) -> str:
        """
        Validate location string.
        
        Args:
            location: Location to validate
            
        Returns:
            Sanitized location
            
        Raises:
            ValidationError: If location is invalid
        """
        if not location or not location.strip():
            raise ValidationError("Location is required")
        
        return Validators.sanitize_string(location, max_length=128)
    
    @staticmethod
    def validate_birth_marks(birth_marks: str) -> Optional[str]:
        """
        Validate birth marks/description.
        
        Args:
            birth_marks: Birth marks to validate
            
        Returns:
            Sanitized birth marks or None if empty
            
        Raises:
            ValidationError: If birth marks is invalid
        """
        if not birth_marks or not birth_marks.strip():
            return None
        
        return Validators.sanitize_string(birth_marks, max_length=512)


def validate_case_registration_form(form_data: dict) -> Tuple[bool, List[str], dict]:
    """
    Validate complete case registration form.
    
    Args:
        form_data: Dictionary containing form fields
        
    Returns:
        Tuple of (is_valid, error_messages, sanitized_data)
    """
    errors = []
    sanitized = {}
    
    try:
        # Required fields
        sanitized['name'] = Validators.validate_name(
            form_data.get('name', ''), 'Name'
        )
        sanitized['last_seen'] = Validators.validate_location(
            form_data.get('last_seen', '')
        )
        sanitized['complainant_name'] = Validators.validate_name(
            form_data.get('complainant_name', ''), 'Complainant Name'
        )
        sanitized['complainant_phone'] = Validators.validate_phone_number(
            form_data.get('complainant_phone', ''), 'Complainant Phone'
        )
        
        # Optional fields
        if form_data.get('father_name'):
            sanitized['father_name'] = Validators.validate_name(
                form_data.get('father_name', ''), "Father's Name"
            )
        else:
            sanitized['father_name'] = ""
        
        if form_data.get('mobile_number'):
            sanitized['mobile_number'] = Validators.validate_phone_number(
                form_data.get('mobile_number', ''), 'Mobile Number'
            )
        else:
            sanitized['mobile_number'] = ""
        
        if form_data.get('adhaar_card'):
            sanitized['adhaar_card'] = Validators.validate_aadhaar(
                form_data.get('adhaar_card', '')
            )
        else:
            sanitized['adhaar_card'] = ""
        
        if form_data.get('address'):
            sanitized['address'] = Validators.validate_address(
                form_data.get('address', '')
            )
        else:
            sanitized['address'] = ""
        
        if form_data.get('city'):
            sanitized['city'] = Validators.validate_city(
                form_data.get('city', '')
            )
        else:
            sanitized['city'] = None
        
        if form_data.get('birthmarks'):
            sanitized['birthmarks'] = Validators.validate_birth_marks(
                form_data.get('birthmarks', '')
            )
        else:
            sanitized['birthmarks'] = ""
        
        if form_data.get('description'):
            sanitized['description'] = Validators.validate_description(
                form_data.get('description', '')
            )
        else:
            sanitized['description'] = None
        
        if form_data.get('complainant_email'):
            sanitized['complainant_email'] = Validators.validate_email(
                form_data.get('complainant_email', '')
            )
        else:
            sanitized['complainant_email'] = None
        
        # Age validation
        age = form_data.get('age', 10)
        if isinstance(age, str):
            try:
                age = int(age)
            except ValueError:
                errors.append("Age must be a valid number")
                return False, errors, {}
        
        sanitized['age'] = Validators.validate_age(age)
        
    except ValidationError as e:
        errors.append(str(e))
        return False, errors, {}
    
    return True, [], sanitized


def validate_public_submission_form(form_data: dict) -> Tuple[bool, List[str], dict]:
    """
    Validate public sighting submission form.
    
    Args:
        form_data: Dictionary containing form fields
        
    Returns:
        Tuple of (is_valid, error_messages, sanitized_data)
    """
    errors = []
    sanitized = {}
    
    try:
        # Required fields
        sanitized['sub_name'] = Validators.validate_name(
            form_data.get('sub_name', ''), 'Your Name'
        )
        sanitized['mobile_number'] = Validators.validate_phone_number(
            form_data.get('mobile_number', ''), 'Mobile Number'
        )
        sanitized['address'] = Validators.validate_location(
            form_data.get('address', '')
        )
        
        # Optional fields
        if form_data.get('email'):
            sanitized['email'] = Validators.validate_email(
                form_data.get('email', '')
            )
        else:
            sanitized['email'] = None
        
        if form_data.get('birth_marks'):
            sanitized['birth_marks'] = Validators.validate_birth_marks(
                form_data.get('birth_marks', '')
            )
        else:
            sanitized['birth_marks'] = None
        
    except ValidationError as e:
        errors.append(str(e))
        return False, errors, {}
    
    return True, [], sanitized