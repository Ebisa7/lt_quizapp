import logging
from telegram import Update, Poll
from telegram.ext import Application, CommandHandler, CallbackContext, PollAnswerHandler
import firebase_admin
from firebase_admin import credentials, firestore

# Firebase Initialization
cred = credentials.Certificate("path/to/your/firebase/credentials.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Telegram Bot Token
TOKEN = "6970014376:AAGEySk5WgjWrUaZp01q3x_qB-VeWohnMPM"

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Dictionary to track user progress
user_progress = {}

async def start(update: Update, context: CallbackContext):
    """Start the quiz for the user."""
    user_id = update.message.from_user.id
    user_progress[user_id] = {"questions": [], "current_index": 0, "score": 0}
    
    # Fetch questions from Firebase
    quiz_ref = db.collection("Science")
    docs = quiz_ref.stream()
    questions = [{"question": doc.to_dict()["question"], "choices": doc.to_dict()["choices"], "correct": doc.to_dict()["correctAnswer"]} for doc in docs]
    
    user_progress[user_id]["questions"] = questions
    
    await send_next_question(update, user_id, context)

async def send_next_question(update: Update, user_id: int, context: CallbackContext):
    """Send the next question as a Telegram poll."""
    user_data = user_progress.get(user_id)
    
    if user_data and user_data["current_index"] < len(user_data["questions"]):
        question_data = user_data["questions"][user_data["current_index"]]
        
        poll_message = await context.bot.send_poll(
            chat_id=user_id,
            question=question_data["question"],
            options=question_data["choices"],
            type=Poll.QUIZ,
            correct_option_id=question_data["choices"].index(question_data["correct"]),
            is_anonymous=False
        )
        
        context.bot_data[poll_message.poll.id] = {"user_id": user_id, "correct": question_data["correct"]}
    else:
        await context.bot.send_message(chat_id=user_id, text=f"Quiz completed! Your score: {user_data['score']} / {len(user_data['questions'])}")

async def handle_poll_answer(update: Update, context: CallbackContext):
    """Handle user responses to the quiz polls."""
    poll_answer = update.poll_answer
    poll_id = poll_answer.poll_id
    user_id = context.bot_data.get(poll_id, {}).get("user_id")
    correct_answer = context.bot_data.get(poll_id, {}).get("correct")
    
    if user_id in user_progress:
        user_data = user_progress[user_id]
        
        if poll_answer.option_ids[0] == user_data["questions"][user_data["current_index"]]["choices"].index(correct_answer):
            user_data["score"] += 1
        
        user_data["current_index"] += 1
        await send_next_question(None, user_id, context)

# Main function to run the bot
async def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(PollAnswerHandler(handle_poll_answer))
    
    await application.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
