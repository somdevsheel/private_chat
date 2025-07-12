import streamlit as st
import pandas as pd
import os
import re
import hashlib
from datetime import datetime

# Ensure required directories exist
os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)

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
if 'show_create_group' not in st.session_state:
    st.session_state.show_create_group = False

# CSV files
CHAT_FILE = "chat_log.csv"
USERS_FILE = "registered_users.csv"
GROUPS_FILE = "groups.csv"

def is_valid_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def generate_user_id(email):
    """Generate a unique user ID based on email"""
    return hashlib.md5(email.encode()).hexdigest()[:8]

def generate_group_id(group_name):
    """Generate a unique group ID based on group name and timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return hashlib.md5(f"{group_name}_{timestamp}".encode()).hexdigest()[:8]

def register_user(email):
    """Register a new user or return existing user info"""
    try:
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
    except Exception as e:
        st.error(f"Error registering user: {e}")
        return None, False

def create_group(group_name, creator_email, members):
    """Create a new group"""
    try:
        group_id = generate_group_id(group_name)
        
        # Add creator to members if not already included
        if creator_email not in members:
            members.append(creator_email)
        
        # Check if groups file exists
        if os.path.exists(GROUPS_FILE):
            groups_df = pd.read_csv(GROUPS_FILE)
        else:
            groups_df = pd.DataFrame(columns=['group_id', 'group_name', 'creator', 'members', 'created_at'])
        
        # Add new group
        new_group = {
            'group_id': group_id,
            'group_name': group_name,
            'creator': creator_email,
            'members': ','.join(members),
            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        groups_df = pd.concat([groups_df, pd.DataFrame([new_group])], ignore_index=True)
        groups_df.to_csv(GROUPS_FILE, index=False)
        
        return group_id, True
    except Exception as e:
        st.error(f"Error creating group: {e}")
        return None, False

def get_user_groups(user_email):
    """Get all groups that the user is a member of"""
    if not os.path.exists(GROUPS_FILE):
        return []
    
    try:
        groups_df = pd.read_csv(GROUPS_FILE)
        user_groups = []
        
        for _, group in groups_df.iterrows():
            members = group['members'].split(',')
            if user_email in members:
                user_groups.append({
                    'group_id': group['group_id'],
                    'group_name': group['group_name'],
                    'creator': group['creator'],
                    'members': members
                })
        
        return user_groups
    except Exception as e:
        st.error(f"Error loading groups: {e}")
        return []

def delete_message(message_index):
    """Delete a message by its index"""
    try:
        if os.path.exists(CHAT_FILE):
            df = pd.read_csv(CHAT_FILE)
            if 0 <= message_index < len(df):
                df = df.drop(df.index[message_index])
                df.to_csv(CHAT_FILE, index=False)
                return True
        return False
    except Exception as e:
        st.error(f"Error deleting message: {e}")
        return False

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
    try:
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
        return True
    except Exception as e:
        st.error(f"Error saving message: {e}")
        return False

def get_filtered_messages(user_email):
    """Get messages that the current user should see"""
    messages = load_messages()
    filtered_messages = []
    user_groups = get_user_groups(user_email)
    user_group_ids = [group['group_id'] for group in user_groups]
    
    for i, msg in enumerate(messages):
        recipient = msg.get('recipient', 'everyone')
        sender_email = msg.get('email', '')
        
        # Show message if:
        # 1. It's a public message (recipient = "everyone")
        # 2. It's sent TO the current user
        # 3. It's sent BY the current user
        # 4. It's sent to a group the user is a member of
        should_show = (
            recipient == "everyone" or 
            recipient == user_email or 
            sender_email == user_email or
            recipient in user_group_ids
        )
        
        if should_show:
            msg['message_index'] = i  # Add index for deletion
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
        message_index = msg.get('message_index', -1)
        display_name = get_user_display_name(email)
        
        # Create a container for each message
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 0.5])
            
            with col1:
                # Determine message type for styling
                is_private = recipient != "everyone"
                is_sent_by_user = email == st.session_state.user_email
                is_group_message = recipient.startswith('group_') if recipient != "everyone" else False
                
                # Get recipient display name
                recipient_display = ""
                if is_private and not is_group_message:
                    recipient_display = f" (Private to {get_user_display_name(recipient)})"
                elif is_group_message:
                    # Find group name
                    user_groups = get_user_groups(st.session_state.user_email)
                    for group in user_groups:
                        if group['group_id'] == recipient:
                            recipient_display = f" (Group: {group['group_name']})"
                            break
                
                if is_sent_by_user:
                    # User's own message - align right
                    bg_color = "#DCF8C6" if not is_private else "#E8F5E8"
                    st.markdown(f"""
                    <div style="background-color: {bg_color}; padding: 10px; border-radius: 10px; margin: 5px 0; text-align: right;">
                        <strong>You{recipient_display}:</strong> {message}
                        <br><small style="color: #666;">ID: {user_id}</small>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    # Other user's message - align left
                    bg_color = "#F1F1F1" if not is_private else "#FFF8DC"
                    privacy_text = " (Private)" if is_private and not is_group_message else ""
                    if is_group_message:
                        privacy_text = " (Group)"
                    st.markdown(f"""
                    <div style="background-color: {bg_color}; padding: 10px; border-radius: 10px; margin: 5px 0;">
                        <strong>{display_name}{privacy_text}:</strong> {message}
                        <br><small style="color: #666;">ID: {user_id} | {email}</small>
                    </div>
                    """, unsafe_allow_html=True)
            
            with col2:
                st.caption(timestamp)
            
            with col3:
                # Show delete button only for user's own messages
                if is_sent_by_user:
                    if st.button("🗑️", key=f"delete_{message_index}", help="Delete message"):
                        if delete_message(message_index):
                            st.success("Message deleted!")
                            st.rerun()
                        else:
                            st.error("Failed to delete message")

def show_user_stats():
    """Show registered users statistics and groups"""
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
        
        # Show user's groups
        user_groups = get_user_groups(st.session_state.user_email)
        if user_groups:
            st.sidebar.subheader("Your Groups")
            for group in user_groups:
                st.sidebar.write(f"• {group['group_name']} ({len(group['members'])} members)")
        
        # Show registered users list
        st.sidebar.subheader("Registered Users")
        current_users = users_df[users_df['email'] != st.session_state.user_email]
        
        if not current_users.empty:
            for _, user in current_users.iterrows():
                display_name = get_user_display_name(user['email'])
                st.sidebar.write(f"• {display_name} ({user['user_id']})")
        else:
            st.sidebar.write("No other users registered yet.")

def show_create_group_form():
    """Show the create group form"""
    st.subheader("Create New Group")
    
    with st.form("create_group_form"):
        group_name = st.text_input("Group Name:", placeholder="Enter group name")
        
        # Get all registered users except current user
        all_users = get_registered_users()
        other_users = [user for user in all_users if user['email'] != st.session_state.user_email]
        
        if other_users:
            st.write("Select members:")
            selected_members = []
            
            for user in other_users:
                display_name = get_user_display_name(user['email'])
                if st.checkbox(f"{display_name} ({user['email']})", key=f"member_{user['email']}"):
                    selected_members.append(user['email'])
            
            create_button = st.form_submit_button("Create Group")
            
            if create_button:
                if group_name.strip():
                    if selected_members:
                        group_id, success = create_group(group_name.strip(), st.session_state.user_email, selected_members)
                        if success:
                            st.success(f"Group '{group_name}' created successfully! Group ID: {group_id}")
                            st.session_state.show_create_group = False
                            st.rerun()
                        else:
                            st.error("Failed to create group")
                    else:
                        st.error("Please select at least one member")
                else:
                    st.error("Please enter a group name")
        else:
            st.info("No other users registered yet. Groups need at least 2 members.")

# Main app logic
def main():
    st.title("💬 Advanced Chat App")
    
    # Login section
    if not st.session_state.logged_in:
        st.header("Login / Register")
        
        st.info("Enter your email to join the chat. Each email gets a unique ID to prevent impersonation.")
        
        email = st.text_input("Enter your email address:", placeholder="user@example.com")
        
        if st.button("Join Chat"):
            if email and is_valid_email(email):
                result = register_user(email)
                if result[0] is not None:
                    user_id, is_new_user = result
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
                    st.error("Failed to register user. Please try again.")
            else:
                st.error("Please enter a valid email address.")
    
    # Chat section
    else:
        # Header with user info and logout
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            display_name = get_user_display_name(st.session_state.user_email)
            st.header(f"Welcome, {display_name}")
            st.caption(f"Email: {st.session_state.user_email} | ID: {st.session_state.user_id}")
        with col2:
            if st.button("Create Group"):
                st.session_state.show_create_group = not st.session_state.show_create_group
                st.rerun()
        with col3:
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.session_state.user_email = ""
                st.session_state.user_id = ""
                st.session_state.messages = []
                st.session_state.selected_recipient = "everyone"
                st.session_state.show_create_group = False
                st.rerun()
        
        # Show user stats in sidebar
        show_user_stats()
        
        # Show create group form if requested
        if st.session_state.show_create_group:
            show_create_group_form()
            st.divider()
        
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
        user_groups = get_user_groups(st.session_state.user_email)
        
        recipient_options = ["everyone (Public)"]
        recipient_values = ["everyone"]
        
        # Add individual users
        for user in other_users:
            display_name = get_user_display_name(user['email'])
            recipient_options.append(f"{display_name} (Private)")
            recipient_values.append(user['email'])
        
        # Add groups
        for group in user_groups:
            recipient_options.append(f"{group['group_name']} (Group)")
            recipient_values.append(group['group_id'])
        
        if len(recipient_options) > 1:
            selected_index = st.selectbox(
                "Send message to:",
                range(len(recipient_options)),
                format_func=lambda x: recipient_options[x],
                index=0
            )
            selected_recipient = recipient_values[selected_index]
        else:
            st.info("No other users or groups available. Your message will be public.")
            selected_recipient = "everyone"
        
        with st.form("message_form", clear_on_submit=True):
            message = st.text_area("Type your message:", height=100, placeholder="Enter your message here...")
            
            submit_button = st.form_submit_button("Send Message")
            
            if submit_button:
                if message.strip():
                    success = save_message(
                        st.session_state.user_email, 
                        st.session_state.user_id, 
                        message.strip(),
                        selected_recipient
                    )
                    
                    if success:
                        st.session_state.messages = load_messages()
                        
                        if selected_recipient == "everyone":
                            st.success("Public message sent!")
                        elif selected_recipient.startswith('group_'):
                            # Find group name
                            group_name = "Unknown Group"
                            for group in user_groups:
                                if group['group_id'] == selected_recipient:
                                    group_name = group['group_name']
                                    break
                            st.success(f"Message sent to group '{group_name}'!")
                        else:
                            recipient_name = get_user_display_name(selected_recipient)
                            st.success(f"Private message sent to {recipient_name}!")
                        
                        st.rerun()
                    else:
                        st.error("Failed to send message. Please try again.")
                else:
                    st.error("Please enter a message.")

if __name__ == "__main__":
    main()
