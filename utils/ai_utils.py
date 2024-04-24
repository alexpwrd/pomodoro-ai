# ai_utils.py

import random

class AIUtils:
    def __init__(self, client, user_name, profession):
        self.client = client
        self.user_name = user_name
        self.profession = profession

    def fetch_motivational_quote(self, for_break=False, current_todo=""):
        themes = [
            "perseverance",
            "efficiency",
            "leadership",
            "learning",
            "growth",
            "adaptability",
            "focus",
            "productivity",
            "balance",
            "well-being",
            "mental clarity",
            "optimism",
            "resilience",
            "innovation",
            "success",
            "energy",
            "motivation",
            "happiness",
            "do what you love"
        ]
        theme = random.choice(themes)
        if not for_break:
            prompt = (
                f"Generate a motivational quote related to {theme} from a successful individual in the {self.profession} industry. This quote should inspire {self.user_name}. "
                f"The user is working on the following task(s) during this work session:'{current_todo}'. Give tips for how to achieve these tasks.  " 
                f"Begin the message with {self.user_name}'s name to grab their attention immediately. Follow with the quote and conclude with a brief reminder of their task, any tips you have for achieving those specific tasks, and encouraging statement that incorporates humor and irony. No coffee references. "
                f"Design this message to be concise, engaging, and easily readable aloud by a voice assistant. No hashtags. The entire message should be a single, impactful paragraph that subtly blends humor/irony with motivation written in a way that will be easy to say by a text to speech model."
            )
        else:
            activities = [
                "deep breathing",
                "quick stretches",
                "a short walk",
                "listening to music",
                "drinking a glass of water",
                "doing a few yoga poses",
                "meditating for a few minutes",
                "doodling or sketching",
                "reading a page of a book",
                "enjoying a healthy snack",
                "stepping outside for fresh air",
                "practicing a quick mindfulness exercise",
                "performing a brief body scan meditation",
                "writing down three things you're grateful for"
            ]
            activity = random.choice(activities)
            prompt = (
                f"Compose a concise, unique, and creative short message for {self.user_name}, who has just finished a work session as a {self.profession} working on: '{current_todo}'. "
                f"Mention the task(s) they are working on and suggest a simple 5 or 10 minute break activity like {activity}. "
                f"Keep the suggestion brief, easy to understand, and suitable for being read aloud by a voice assistant. "
                f"Focus on activities that are scientifically proven to reduce stress and enhance focus. "
                f"Add a touch of humor or irony to lighten the mood—because even serious break activities can have a fun side."
            )

        chat_completion = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": f"You are a motivational AI assistant to a {self.profession} named {self.user_name} who is working on these tasks during a Pomodoro 25 min work session: '{current_todo}'. Aim for uniqueness, creativity, humour, and scientific grounding in your messages. Your messages will be read out loud to the user to format them in a way that would be easy for an apple OS voice to say out loud. "},
                {"role": "user", "content": prompt}
            ],
            model="gpt-3.5-turbo",
            temperature=0.8,
            max_tokens=200
        )
        return chat_completion.choices[0].message.content.strip()