import streamlit as st
from sqlalchemy import create_engine
from langchain.chat_models import ChatOpenAI
from langchain_experimental.sql import SQLDatabaseChain
from langchain.sql_database import SQLDatabase
from langchain.prompts.chat import HumanMessagePromptTemplate
from langchain.schema import SystemMessage
import os
import time
from datetime import datetime

# --- Page Configuration ---
st.set_page_config(
    page_title=" Student Migration Analytics",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Database Initialization Functions ---
def initialize_database():
    """Initialize database connection with error handling"""
    try:
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR API KEY")
        
        if not OPENAI_API_KEY:
            st.error("⚠️ OpenAI API key not found!")
            return None, None, None
        
        llm = ChatOpenAI(temperature=0, openai_api_key=OPENAI_API_KEY)
        
        # Database connection
        host = 'localhost'
        port = '3306'
        username = 'root'
        database_schema = 'sahasra'
        mysql_uri = f"mysql+pymysql://{username}@{host}:{port}/{database_schema}"
        
        db = SQLDatabase.from_uri(
            mysql_uri, 
            include_tables=['global_student_migration'], 
            sample_rows_in_table_info=2
        )
        
        db_chain = SQLDatabaseChain.from_llm(llm, db, verbose=True)
        
        st.session_state.db_connected = True
        return llm, db, db_chain
        
    except Exception as e:
        st.error(f"❌ Database connection failed: {str(e)}")
        st.session_state.db_connected = False
        return None, None, None

def retrieve_from_db(query: str, db_chain) -> str:
    """Retrieve data from database with error handling"""
    try:
        db_context = db_chain(query)
        return db_context['result'].strip()
    except Exception as e:
        return f"Error retrieving data: {str(e)}"

def generate_response(query: str, llm, db_chain) -> str:
    """Generate response using LLM"""
    try:
        db_context = retrieve_from_db(query, db_chain)
        
        system_message = """You are a student migration data expert and analyst.
Your task is to answer user questions using information from a SQL database about global student migration patterns.
Base your answer only on the given context and provide insights when possible.

Guidelines:
- Be conversational and helpful
- Provide specific numbers when available
- Offer context about trends when relevant
- If data is limited, acknowledge it
- Use emojis sparingly but appropriately

Example:
Input: How many students went to Canada?
Context: There are 120 students in the database who went to Canada.
Output: Based on the data, 120 students have migrated to Canada for higher studies. Canada continues to be a popular destination for international students!
"""

        human_qry_template = HumanMessagePromptTemplate.from_template(
            """Input:
{human_input}

Context:
{db_context}

Output:
"""
        )

        messages = [
            SystemMessage(content=system_message),
            human_qry_template.format(human_input=query, db_context=db_context)
        ]

        response = llm(messages).content
        return response
        
    except Exception as e:
        return f"Sorry, I encountered an error while processing your question: {str(e)}"

# --- New function to process a question and update chat history ---
def process_question(question: str) -> bool:
    """
    Processes a user question, generates a response, and updates chat history.
    Returns True if successful, False otherwise.
    """
    if question.lower().strip() in ["exit", "quit", "bye", "goodbye"]:
        st.success("👋 **Thank you for using Student Migration Analytics!**")
        st.info("Feel free to ask more questions anytime.")
        st.balloons()
        return True # Or handle exit state separately
    
    # Add user message to history
    st.session_state.chat_history.append(("You", question))
    
    # Show processing status
    with st.spinner("🤔 Analyzing your question and querying the database..."):
        progress_bar = st.progress(0)
        progress_bar.progress(25)
        
        try:
            # Generate response
            response = generate_response(
                question, 
                st.session_state.llm, 
                st.session_state.db_chain
            )
            
            progress_bar.progress(75)
            
            # Add bot response to history
            st.session_state.chat_history.append(("Bot", response))
            
            progress_bar.progress(100)
            time.sleep(0.5)
            progress_bar.empty()
            
            st.success("✅ Response generated successfully!")
            return True
            
        except Exception as e:
            progress_bar.empty()
            st.error(f"❌ **Error Occurred**: {str(e)}")
            st.warning("Please try rephrasing your question or check the system status.")
            return False

# --- Sidebar Configuration ---
with st.sidebar:
    st.header("🎓 Student Migration Analytics")
    
    # Database Status Section
    st.subheader("📊 System Status")
    if "db_connected" not in st.session_state:
        st.session_state.db_connected = False
    
    if st.session_state.db_connected:
        st.success("✅ Database Connected")
    else:
        st.error("❌ Database Disconnected")
    
    st.divider()
    
    # Chat Statistics
    st.subheader("📈 Chat Statistics")
    chat_count = len(st.session_state.get("chat_history", [])) // 2
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Questions Asked", chat_count)
    with col2:
        st.metric("Active Session", "Yes" if st.session_state.get("initialized", False) else "No")
    
    st.divider()
    
    # Quick Actions
    st.subheader("⚡ Quick Actions")
    
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.chat_history = []
        st.success("Chat history cleared!")
        time.sleep(1)
        st.rerun()
    
    if st.button("📊 Show Database Info", use_container_width=True):
        st.session_state.show_db_info = True
    
    st.divider()
    
    # Sample Questions
    st.subheader("💡 Sample Questions")
    st.caption("Click on any question to ask it directly:")
    
    sample_questions = [
        "How many students went to Canada?",
        "Which country has the most students?",
        "Show me migration trends by year",
        "What are the top 5 destinations?",
        "How many students from India?",
        "What is the average age of migrating students?",
        "Which field of study is most popular?"
    ]
    
    for i, question in enumerate(sample_questions):
        if st.button(f"❓ {question}", key=f"sample_{i}", use_container_width=True):
            if st.session_state.get("db_connected", False):
                # We store the selected question in session state
                # and trigger a rerun. The main part of the app
                # will then pick it up and process it via the form.
                st.session_state.selected_question = question
                st.rerun() # Trigger a rerun to process the question through the main form
            else:
                st.error("❌ Database not connected!")
    
    st.divider()
    
    # Information Section
    st.subheader("ℹ️ How to Use")
    st.info("""
    1. **Ask Questions**: Type your question in natural language
    2. **Use Samples**: Click sample questions for quick queries
    3. **View History**: Scroll through past conversations
    4. **Clear Data**: Use quick actions to reset
    """)
    
    st.subheader("🔧 Tips")
    st.info("""
    - Be specific in your questions
    - Ask about countries, years, or trends
    - Use simple, clear language
    - Check database status if issues occur
    """)

# --- Main Application ---
st.title("🎓 Student Migration Analytics Chatbot")
st.markdown("**Get insights from global student migration data through natural language queries**")

# Initialize components
if "initialized" not in st.session_state:
    with st.spinner("🔄 Initializing system components..."):
        progress_bar = st.progress(0)
        progress_bar.progress(25)
        
        llm, db, db_chain = initialize_database()
        progress_bar.progress(75)
        
        st.session_state.llm = llm
        st.session_state.db = db
        st.session_state.db_chain = db_chain
        st.session_state.initialized = True
        progress_bar.progress(100)
        
        time.sleep(0.5)
        progress_bar.empty()

# Initialize chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Check if system is properly initialized
if not st.session_state.get("db_connected", False):
    st.error("⚠️ **System Not Ready**")
    st.warning("Please check your database connection and OpenAI API key configuration.")
    
    with st.expander("🔧 Troubleshooting"):
        st.write("**Common Issues:**")
        st.write("- Database server not running")
        st.write("- Incorrect database credentials")
        st.write("- Network connectivity issues")
        st.write("- Invalid OpenAI API key")
        
        if st.button("🔄 Retry Connection"):
            st.session_state.initialized = False
            st.rerun()
    
    st.stop()

# Show database info if requested
if st.session_state.get("show_db_info", False):
    st.subheader("📊 Database Information")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info("**Database**: sahasra")
    with col2:
        st.info("**Table**: global_student_migration")
    with col3:
        st.info("**Host**: localhost:3306")
    
    if st.button("❌ Hide Database Info"):
        st.session_state.show_db_info = False
        st.rerun()
    
    st.divider()

# Display welcome message if no chat history
if not st.session_state.chat_history:
    st.success("🎉 **Welcome to Student Migration Analytics!**")
    st.info("Ask me anything about student migration patterns, popular destinations, or specific statistics.")
    
    # Show example interactions
    with st.expander("📚 Example Interactions"):
        st.write("**Question**: How many students went to Canada?")
        st.write("**Answer**: Based on the data, 120 students have migrated to Canada for higher studies. 🇨🇦")
        st.write("---")
        st.write("**Question**: Which country is most popular?")
        st.write("**Answer**: The United States leads with 450 students, followed by Canada and the UK.")

# Chat Display Area
if st.session_state.chat_history:
    st.subheader("💬 Chat History")
    
    # Display chat history in chronological order
    for i in range(0, len(st.session_state.chat_history), 2):
        if i + 1 < len(st.session_state.chat_history):
            user_msg = st.session_state.chat_history[i][1]
            bot_msg = st.session_state.chat_history[i + 1][1]
            
            # Create chat bubble containers
            with st.container():
                # User message
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.info(f"**🧑 You**: {user_msg}")
                
                # Bot message
                col1, col2 = st.columns([1, 3])
                with col2:
                    st.success(f"**🤖 Assistant**: {bot_msg}")
                
                st.write("")  # Add spacing

# Input Section
st.divider()
st.subheader("💭 Ask Your Question")

# Handle selected question from sidebar
if "selected_question" in st.session_state and st.session_state.selected_question:
    default_question = st.session_state.selected_question
    # We will clear it after the form is submitted to avoid re-populating on subsequent reruns
else:
    default_question = ""

# Create input form
with st.form("chat_form", clear_on_submit=True):
    # Input field
    user_input = st.text_input(
        "Type your question here:",
        value=default_question, # Use the selected question as default
        placeholder="e.g., How many students went to Canada for Computer Science?",
        help="💡 Ask about migration patterns, countries, statistics, trends, or specific demographics",
        key="main_chat_input" # Add a key to the text_input
    )
    
    # Form buttons
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        submitted = st.form_submit_button("🚀 Send Message", use_container_width=True, type="primary")
    with col2:
        clear_input = st.form_submit_button("🗑️ Clear", use_container_width=True)
    with col3:
        help_button = st.form_submit_button("❓ Help", use_container_width=True)

# Handle form submission
if submitted and user_input:
    process_question(user_input)
    # Clear the selected_question after it's processed by the form
    if "selected_question" in st.session_state:
        del st.session_state.selected_question 
    st.rerun() # Rerun to display the updated chat history

# Handle clear input
if clear_input:
    st.info("Input cleared!")
    # Also clear the default_question if it was set from a sample
    if "selected_question" in st.session_state:
        del st.session_state.selected_question
    st.rerun()

# Handle help request
if help_button:
    st.info("**Help**: Use natural language to ask questions about student migration data!")
    with st.expander("🔍 Query Examples"):
        st.write("- How many students went to [country]?")
        st.write("- Which country has the most students?")
        st.write("- Show migration trends by year")
        st.write("- What are the top destinations?")
        st.write("- How many students study [field]?")

# Footer Information
st.divider()

# Statistics row
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Questions", len(st.session_state.get("chat_history", [])) // 2)
with col2:
    st.metric("System Status", "Online" if st.session_state.get("db_connected", False) else "Offline")
with col3:
    st.metric("Database", "Connected" if st.session_state.get("db_connected", False) else "Disconnected")
with col4:
    st.metric("Session", "Active" if st.session_state.get("initialized", False) else "Inactive")

# Footer text
st.caption("🎓 Student Migration Analytics Chatbot | Powered by OpenAI & LangChain")
st.caption("Ask questions about global student migration patterns and get data-driven insights!")