"""
Authentication and verification module for public portal security.
"""
import os
import random
import string
import hashlib
import json
import time
from typing import Optional, Tuple
from datetime import datetime, timedelta
import streamlit as st


class CaptchaGenerator:
    """Simple text-based CAPTCHA for preventing automated submissions."""
    
    @staticmethod
    def generate_captcha(length: int = 6) -> Tuple[str, str]:
        """
        Generate a simple text CAPTCHA.
        
        Args:
            length: Length of CAPTCHA string
            
        Returns:
            Tuple of (captcha_text, captcha_id)
        """
        # Generate random alphanumeric string
        chars = string.ascii_uppercase + string.digits
        captcha_text = ''.join(random.choice(chars) for _ in range(length))
        
        # Create a simple hash for verification
        captcha_id = hashlib.md5(
            f"{captcha_text}{time.time()}".encode()
        ).hexdigest()[:12]
        
        return captcha_text, captcha_id
    
    @staticmethod
    def verify_captcha(user_input: str, captcha_text: str) -> bool:
        """
        Verify user's CAPTCHA input.
        
        Args:
            user_input: User's input
            captcha_text: Original CAPTCHA text
            
        Returns:
            True if valid, False otherwise
        """
        if not user_input or not captcha_text:
            return False
        
        return user_input.upper().strip() == captcha_text.upper().strip()


class RateLimiter:
    """Simple in-memory rate limiter for preventing abuse."""
    
    def __init__(self):
        self.requests = {}  # IP -> list of timestamps
        self.max_requests = 10  # Max requests per window
        self.window_seconds = 3600  # 1 hour window
    
    def is_allowed(self, identifier: str) -> Tuple[bool, Optional[str]]:
        """
        Check if request is allowed based on rate limits.
        
        Args:
            identifier: Unique identifier (IP, session ID, etc.)
            
        Returns:
            Tuple of (is_allowed, error_message)
        """
        current_time = time.time()
        
        if identifier not in self.requests:
            self.requests[identifier] = []
        
        # Remove old requests outside the time window
        self.requests[identifier] = [
            ts for ts in self.requests[identifier]
            if current_time - ts < self.window_seconds
        ]
        
        # Check if under limit
        if len(self.requests[identifier]) >= self.max_requests:
            return False, f"Rate limit exceeded. Maximum {self.max_requests} submissions per hour."
        
        # Add current request
        self.requests[identifier].append(current_time)
        return True, None
    
    def get_remaining_requests(self, identifier: str) -> int:
        """Get remaining requests for identifier."""
        if identifier not in self.requests:
            return self.max_requests
        
        current_time = time.time()
        self.requests[identifier] = [
            ts for ts in self.requests[identifier]
            if current_time - ts < self.window_seconds
        ]
        
        return self.max_requests - len(self.requests[identifier])


class SessionManager:
    """Manage user sessions for public portal."""
    
    def __init__(self):
        self.sessions = {}  # session_id -> session_data
        self.session_timeout = 1800  # 30 minutes
    
    def create_session(self) -> str:
        """Create a new session and return session ID."""
        session_id = hashlib.md5(
            f"{random.random()}{time.time()}".encode()
        ).hexdigest()
        
        self.sessions[session_id] = {
            'created_at': time.time(),
            'last_activity': time.time(),
            'submission_count': 0,
            'verified': False
        }
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session data if valid."""
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        
        # Check if session is expired
        if time.time() - session['last_activity'] > self.session_timeout:
            del self.sessions[session_id]
            return None
        
        # Update last activity
        session['last_activity'] = time.time()
        return session
    
    def update_session(self, session_id: str, **kwargs):
        """Update session data."""
        if session_id in self.sessions:
            self.sessions[session_id].update(kwargs)
    
    def is_verified(self, session_id: str) -> bool:
        """Check if session is verified."""
        session = self.get_session(session_id)
        return session and session.get('verified', False)
    
    def increment_submission_count(self, session_id: str):
        """Increment submission count for session."""
        session = self.get_session(session_id)
        if session:
            session['submission_count'] = session.get('submission_count', 0) + 1


class EmailVerifier:
    """Simple email verification simulation (in production, use real email service)."""
    
    @staticmethod
    def generate_verification_code() -> str:
        """Generate a 6-digit verification code."""
        return ''.join(random.choice(string.digits) for _ in range(6))
    
    @staticmethod
    def send_verification_email(email: str, code: str) -> bool:
        """
        Simulate sending verification email.
        In production, integrate with real email service.
        
        Args:
            email: Recipient email
            code: Verification code
            
        Returns:
            True if successful (simulated)
        """
        # In production, this would send a real email
        # For now, we'll just log it for demonstration
        print(f"[SIMULATED EMAIL] To: {email}, Code: {code}")
        return True
    
    @staticmethod
    def verify_code(user_code: str, actual_code: str) -> bool:
        """Verify the user's input code."""
        return user_code.strip() == actual_code.strip()


# Global instances
rate_limiter = RateLimiter()
session_manager = SessionManager()


def get_client_identifier() -> str:
    """
    Get a unique identifier for the client.
    In production, this would use IP address or similar.
    For Streamlit, we use session state.
    """
    if 'client_id' not in st.session_state:
        st.session_state['client_id'] = hashlib.md5(
            f"{random.random()}{time.time()}".encode()
        ).hexdigest()
    
    return st.session_state['client_id']


def check_rate_limit() -> Tuple[bool, Optional[str]]:
    """
    Check if the current client is within rate limits.
    
    Returns:
        Tuple of (is_allowed, error_message)
    """
    client_id = get_client_identifier()
    return rate_limiter.is_allowed(client_id)


def get_remaining_submissions() -> int:
    """Get remaining submissions for current client."""
    client_id = get_client_identifier()
    return rate_limiter.get_remaining_requests(client_id)


def initialize_session() -> str:
    """Initialize or get existing session."""
    if 'session_id' not in st.session_state:
        st.session_state['session_id'] = session_manager.create_session()
    
    return st.session_state['session_id']


def render_captcha() -> Tuple[str, str]:
    """
    Render CAPTCHA challenge in Streamlit with session state management.
    
    Returns:
        Tuple of (captcha_text, user_input)
    """
    # Initialize CAPTCHA in session state if not exists
    if 'captcha_text' not in st.session_state or 'captcha_verified' not in st.session_state:
        st.session_state['captcha_text'], st.session_state['captcha_id'] = CaptchaGenerator.generate_captcha()
        st.session_state['captcha_verified'] = False
    
    # Only regenerate if verification failed explicitly
    if st.session_state.get('captcha_regenerate', False):
        st.session_state['captcha_text'], st.session_state['captcha_id'] = CaptchaGenerator.generate_captcha()
        st.session_state['captcha_verified'] = False
        st.session_state['captcha_regenerate'] = False
    
    captcha_text = st.session_state['captcha_text']
    
    # Display CAPTCHA (simple text-based for now)
    st.markdown("### Security Verification")
    st.write(f"**Enter the following code:** `{captcha_text}`")
    
    # Add some visual distortion (in text form)
    st.caption("This helps prevent automated submissions")
    
    user_input = st.text_input("Security Code", key="captcha_input", max_chars=6)
    
    return captcha_text, user_input


def render_email_verification(email: str) -> Tuple[str, str]:
    """
    Render email verification flow.
    
    Args:
        email: Email address to verify
        
    Returns:
        Tuple of (verification_code, user_input)
    """
    if 'verification_code' not in st.session_state:
        st.session_state['verification_code'] = EmailVerifier.generate_verification_code()
        st.session_state['code_sent'] = False
    
    verification_code = st.session_state['verification_code']
    
    if not st.session_state['code_sent']:
        if st.button("Send Verification Code"):
            if EmailVerifier.send_verification_email(email, verification_code):
                st.session_state['code_sent'] = True
                st.success(f"Verification code sent to {email}")
                st.info(f"[DEMO MODE] Your verification code is: {verification_code}")
            else:
                st.error("Failed to send verification code")
    
    if st.session_state['code_sent']:
        user_code = st.text_input("Enter Verification Code", max_chars=6)
        return verification_code, user_code
    
    return verification_code, ""


def verify_session() -> bool:
    """
    Verify current session is authenticated.
    
    Returns:
        True if session is verified
    """
    session_id = initialize_session()
    return session_manager.is_verified(session_id)


def mark_session_verified():
    """Mark current session as verified."""
    session_id = initialize_session()
    session_manager.update_session(session_id, verified=True)


def render_auth_flow(required: bool = True) -> bool:
    """
    Render complete authentication flow for public portal.
    
    Args:
        required: Whether authentication is required
        
    Returns:
        True if authenticated, False otherwise
    """
    st.markdown("---")
    st.markdown("### 🔐 Security Verification")
    
    # Check if already verified in this session
    if st.session_state.get('captcha_verified', False):
        st.success("✅ Security verification complete")
        return True
    
    # Check rate limits first
    is_allowed, rate_error = check_rate_limit()
    if not is_allowed:
        st.error(rate_error)
        remaining = get_remaining_submissions()
        st.info(f"Please try again later. Remaining submissions: {remaining}")
        return False
    
    # Show remaining submissions
    remaining = get_remaining_submissions()
    st.caption(f"Remaining submissions: {remaining}")
    
    # CAPTCHA verification
    captcha_text, user_input = render_captcha()
    
    # Add verify button
    verify_button = st.button("Verify Security Code")
    
    if verify_button:
        if not user_input:
            st.error("❌ Please enter the security code")
            st.session_state['captcha_regenerate'] = False
        elif not CaptchaGenerator.verify_captcha(user_input, captcha_text):
            st.error("❌ Incorrect security code. Please try again.")
            st.session_state['captcha_regenerate'] = True  # Regenerate on next run
        else:
            st.success("✅ Security verification complete")
            st.session_state['captcha_verified'] = True
            st.session_state['captcha_regenerate'] = False
            st.rerun()  # Rerun to clear the CAPTCHA form
    
    # If required and not verified, return False
    if required and not st.session_state.get('captcha_verified', False):
        return False
    
    return st.session_state.get('captcha_verified', False)