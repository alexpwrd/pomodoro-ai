# ai_utils.py

import random

class AIUtils:
    def __init__(self, client, user_name, profession):
        self.client = client
        self.user_name = user_name
        self.profession = profession

    def fetch_motivational_quote(self, for_break=False, current_todo="", is_long_break=False):
        themes = [
            "perseverance", "efficiency", "leadership", "learning", "growth",
            "adaptability", "focus", "productivity", "balance", "well-being",
            "mental clarity", "optimism", "resilience", "innovation", "success",
            "energy", "motivation", "happiness", "do what you love"
        ]
        theme = random.choice(themes)
        
        if not for_break:
            prompt = (
                f"Generate a motivational quote related to {theme} from a successful individual in the {self.profession} industry. This quote should inspire {self.user_name}. "
                f"The user is working on the following task(s) during this work session:'{current_todo}'. Give tips for how to make progress on these tasks.  " 
                f"Begin the message with {self.user_name}'s name to grab their attention immediately. Follow with the quote and conclude with a brief reminder of their task, any tips you have for making progress on those specific tasks, and an encouraging statement that incorporates humor and irony. No coffee references. "
                f"Design this message to be concise, engaging, and easily readable aloud by a voice assistant. No hashtags. The entire message should be a single, impactful paragraph that subtly blends humor/irony with motivation written in a way that will be easy to say by a text to speech model."
            )
        elif is_long_break:
            activities = [
                "take a power nap", "go for a brisk walk", "practice mindfulness meditation",
                "do some light exercise", "prepare a healthy snack", "engage in a hobby",
                "call a friend or family member", "tidy up your workspace",
                "plan your next work cycle", "reflect on your progress"
            ]
            activity = random.choice(activities)
            prompt = (
                f"Compose an enthusiastic message for {self.user_name}, a {self.profession} who has completed a full work cycle of four Pomodoro sessions! "
                f"Acknowledge their effort and suggest they take a longer break of about 15-30 minutes to recharge. "
                f"Recommend they use this time to {activity}, explaining how this can refresh their mind and boost productivity for the next work cycle. "
                f"Briefly mention their ongoing tasks: '{current_todo}', and how this break will help them approach these tasks with renewed energy. "
                f"Emphasize the importance of taking this longer break to maintain long-term productivity and prevent burnout. "
                f"Include a touch of humor or playful irony to keep the tone light and engaging. "
                f"Encourage them to fully disconnect during this break and return refreshed for the next cycle. "
                f"Ensure the message is concise, uplifting, and easy for a voice assistant to read aloud. "
                f"End with a motivational statement that ties into their profession and the concept of work cycles, encouraging them to keep pushing forward."
            )
        else:
            activities = [
                "deep breathing", "quick stretches", "a short walk", "listening to music",
                "drinking a glass of water", "doing a few yoga poses", "meditating for a few minutes",
                "doodling or sketching", "reading a page of a book", "enjoying a healthy snack",
                "stepping outside for fresh air", "practicing a quick mindfulness exercise",
                "performing a brief body scan meditation", "writing down three things you're grateful for"
            ]
            activity = random.choice(activities)
            prompt = (
                f"Compose a concise, unique, and creative short message for {self.user_name}, a {self.profession} who has just completed a work session and is working on: '{current_todo}'. "
                f"Acknowledge their effort so far and suggest a simple 5 or 10 minute break activity like {activity}. "
                f"Explain how this break can help them return to their tasks with renewed focus and energy. "
                f"Keep the suggestion brief, easy to understand, and suitable for being read aloud by a voice assistant. "
                f"Focus on activities that are scientifically proven to reduce stress and enhance focus. "
                f"Add a touch of humor or irony to lighten the mood—because even serious break activities can have a fun side. "
                f"Conclude with an encouraging note about tackling their tasks after the break."
            )

        chat_completion = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": f"You are a motivational AI assistant to a {self.profession} named {self.user_name} who is working on these tasks during a Pomodoro work session: '{current_todo}'. Aim for uniqueness, creativity, humour, and scientific grounding in your messages. Your messages will be read out loud to the user so format them in a way that would be easy for an apple OS voice to say out loud. "},
                {"role": "user", "content": prompt}
            ],
            model="gpt-4-turbo",
            temperature=0.8,
            max_tokens=400
        )
        return chat_completion.choices[0].message.content.strip()