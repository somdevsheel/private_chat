import streamlit as st
import pandas as pd
import os
import re
import hashlib
from datetime import datetime

# Set page config
st.set_page_config(page_title="Chat App", page_icon="💬", layout="wide")

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = ""
if 'user_id' not in st.session_state:
    st.session_state.user_id = ""
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'selected_recipient' not in st.session_state:
    st.session_state.selected_recipient = "everyone"

# CSV files
CHAT_FILE = "chat_log.csv"
USERS_FILE = "registered_users.csv"

def is_valid_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def generate_user_id(email):
    """Generate a unique user ID based on email"""
    return hashlib.md5(email.encode()).hexdigest()[:8]

def register_user(email):
    """Register a new user or return existing user info"""
    user_id = generate_user_id(email)
    
    # Check if users file exists
    if os.path.exists(USERS_FILE):
        users_df = pd.read_csv(USERS_FILE)
        # Check if user already exists
        if email in users_df['email'].values:
            return user_id, False  # User exists
    else:
        users_df = pd.DataFrame(columns=['email', 'user_id', 'first_login'])
    
    # Add new user
    new_user = {
        'email': email,
        'user_id': user_id,
        'first_login': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    users_df = pd.concat([users_df, pd.DataFrame([new_user])], ignore_index=True)
    users_df.to_csv(USERS_FILE, index=False)
    
    return user_id, True  # New user

def get_user_display_name(email):
    """Get a display name for the user"""
    return email.split('@')[0]

def get_registered_users():
    """Get list of all registered users"""
    if os.path.exists(USERS_FILE):
        users_df = pd.read_csv(USERS_FILE)
        return users_df[['email', 'user_id']].to_dict('records')
    return []

def load_messages():
    """Load messages from CSV file"""
    if os.path.exists(CHAT_FILE):
        try:
            df = pd.read_csv(CHAT_FILE)
            # Ensure recipient column exists for backwards compatibility
            if 'recipient' not in df.columns:
                df['recipient'] = 'everyone'
                df.to_csv(CHAT_FILE, index=False)
            return df.to_dict('records')
        except Exception as e:
            st.error(f"Error loading messages: {e}")
            return []
    return []

def save_message(email, user_id, message, recipient="everyone"):
    """Save a new message to CSV file with user verification"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_row = {
        'timestamp': timestamp,
        'email': email,
        'user_id': user_id,
        'message': message,
        'recipient': recipient
    }
    
    if os.path.exists(CHAT_FILE):
        df = pd.read_csv(CHAT_FILE)
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    else:
        df = pd.DataFrame([new_row])
    
    df.to_csv(CHAT_FILE, index=False)

def get_filtered_messages(user_email):
    """Get messages that the current user should see"""
    messages = load_messages()
    filtered_messages = []
    
    for msg in messages:
        recipient = msg.get('recipient', 'everyone')
        sender_email = msg.get('email', '')
        
        # Show message if:
        # 1. It's a public message (recipient = "everyone")
        # 2. It's sent TO the current user
        # 3. It's sent BY the current user
        if (recipient == "everyone" or 
            recipient == user_email or 
            sender_email == user_email):
            filtered_messages.append(msg)
    
    return filtered_messages

def display_messages():
    """Display messages that the current user should see"""
    messages = get_filtered_messages(st.session_state.user_email)
    
    if not messages:
        st.info("No messages yet. Start the conversation!")
        return
    
    # Display messages in reverse order (newest first)
    for msg in reversed(messages):
        timestamp = msg['timestamp']
        email = msg['email']
        user_id = msg.get('user_id', 'unknown')
        message = msg['message']
        recipient = msg.get('recipient', 'everyone')
        display_name = get_user_display_name(email)
        
        # Create a container for each message
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # Determine message type for styling
                is_private = recipient != "everyone"
                is_sent_by_user = email == st.session_state.user_email
                is_sent_to_user = recipient == st.session_state.user_email
                
                if is_sent_by_user:
                    # User's own message - align right
                    bg_color = "#DCF8C6" if not is_private else "#E8F5E8"
                    privacy_text = f" (Private to {get_user_display_name(recipient)})" if is_private else ""
                    st.markdown(f"""
                    <div style="background-color: {bg_color}; padding: 10px; border-radius: 10px; margin: 5px 0; text-align: right;">
                        <strong>You{privacy_text}:</strong> {message}
                        <br><small style="color: #666;">ID: {user_id}</small>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # Other user's message - align left
                    bg_color = "#F1F1F1" if not is_private else "#FFF8DC"
                    privacy_text = " (Private)" if is_private else ""
                    st.markdown(f"""
                    <div style="background-color: {bg_color}; padding: 10px; border-radius: 10px; margin: 5px 0;">
                        <strong>{display_name}{privacy_text}:</strong> {message}
                        <br><small style="color: #666;">ID: {user_id} | {email}</small>
                    </div>
                    """, unsafe_allow_html=True)
            
            with col2:
                st.caption(timestamp)

def show_user_stats():
    """Show registered users statistics and allow selection"""
    if os.path.exists(USERS_FILE):
        users_df = pd.read_csv(USERS_FILE)
        st.sidebar.subheader("Chat Statistics")
        st.sidebar.write(f"Total registered users: {len(users_df)}")
        
        if os.path.exists(CHAT_FILE):
            chat_df = pd.read_csv(CHAT_FILE)
            st.sidebar.write(f"Total messages: {len(chat_df)}")
            
            # Count private vs public messages
            if 'recipient' in chat_df.columns:
                public_msgs = len(chat_df[chat_df['recipient'] == 'everyone'])
                private_msgs = len(chat_df) - public_msgs
            else:
                # For backwards compatibility with old chat logs
                public_msgs = len(chat_df)
                private_msgs = 0
            st.sidebar.write(f"Public messages: {public_msgs}")
            st.sidebar.write(f"Private messages: {private_msgs}")
        
        # Show registered users list
        st.sidebar.subheader("Registered Users")
        current_users = users_df[users_df['email'] != st.session_state.user_email]
        
        if not current_users.empty:
            for _, user in current_users.iterrows():
                display_name = get_user_display_name(user['email'])
                st.sidebar.write(f"• {display_name} ({user['user_id']})")
        else:
            st.sidebar.write("No other users registered yet.")

# Main app logic
def main():
    st.title("💬 Secure Chat App with Private Messages")
    
    # Login section
    if not st.session_state.logged_in:
        st.header("Login / Register")
        
        st.info("Enter your email to join the chat. Each email gets a unique ID to prevent impersonation.")
        
        email = st.text_input("Enter your email address:", placeholder="user@example.com")
        
        if st.button("Join Chat"):
            if email and is_valid_email(email):
                user_id, is_new_user = register_user(email)
                st.session_state.logged_in = True
                st.session_state.user_email = email
                st.session_state.user_id = user_id
                st.session_state.messages = load_messages()
                
                if is_new_user:
                    st.success(f"Welcome! Your unique ID is: {user_id}")
                else:
                    st.success(f"Welcome back! Your ID is: {user_id}")
                
                st.rerun()
            else:
                st.error("Please enter a valid email address.")
    
    # Chat section
    else:
        # Header with user info and logout
        col1, col2 = st.columns([3, 1])
        with col1:
            display_name = get_user_display_name(st.session_state.user_email)
            st.header(f"Welcome, {display_name}")
            st.caption(f"Email: {st.session_state.user_email} | ID: {st.session_state.user_id}")
        with col2:
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.session_state.user_email = ""
                st.session_state.user_id = ""
                st.session_state.messages = []
                st.session_state.selected_recipient = "everyone"
                st.rerun()
        
        # Show user stats in sidebar
        show_user_stats()
        
        # Chat display area
        st.subheader("Chat Messages")
        
        # Refresh button
        if st.button("🔄 Refresh Chat"):
            st.session_state.messages = load_messages()
            st.rerun()
        
        # Display messages
        display_messages()
        
        # Message input section
        st.subheader("Send a Message")
        
        # Recipient selection
        registered_users = get_registered_users()
        other_users = [user for user in registered_users if user['email'] != st.session_state.user_email]
        
        recipient_options = ["everyone (Public)"]
        recipient_values = ["everyone"]
        
        for user in other_users:
            display_name = get_user_display_name(user['email'])
            recipient_options.append(f"{display_name} (Private)")
            recipient_values.append(user['email'])
        
        if len(recipient_options) > 1:
            selected_index = st.selectbox(
                "Send message to:",
                range(len(recipient_options)),
                format_func=lambda x: recipient_options[x],
                index=0
            )
            selected_recipient = recipient_values[selected_index]
        else:
            st.info("No other users registered yet. Your message will be public.")
            selected_recipient = "everyone"
        
        with st.form("message_form", clear_on_submit=True):
            message = st.text_area("Type your message:", height=100, placeholder="Enter your message here...")
            
            submit_button = st.form_submit_button("Send Message")
            
            if submit_button:
                if message.strip():
                    save_message(
                        st.session_state.user_email, 
                        st.session_state.user_id, 
                        message.strip(),
                        selected_recipient
                    )
                    st.session_state.messages = load_messages()
                    
                    if selected_recipient == "everyone":
                        st.success("Public message sent!")
                    else:
                        recipient_name = get_user_display_name(selected_recipient)
                        st.success(f"Private message sent to {recipient_name}!")
                    
                    st.rerun()
                else:
                    st.error("Please enter a message.")

if __name__ == "__main__":
    main()