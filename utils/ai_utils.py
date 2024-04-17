# ai_utils.py

import random

class AIUtils:
    def __init__(self, client, user_name, profession, company):
        self.client = client
        self.user_name = user_name
        self.profession = profession
        self.company = company

    def fetch_motivational_quote(self, for_break=False):
        themes = [
            "perseverance",
            "efficiency",
            "teamwork",
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
                f"Generate a motivational quote related to {theme} from a successful individual in the {self.profession} industry. This quote should inspire {self.user_name}, who is about to start a work session at {self.company}. "
                f"Begin the message with {self.user_name}'s name to grab their attention immediately. Follow with the quote and conclude with a brief, encouraging statement that incorporates humor and irony. No coffee references. "
                f"Design this message to be concise, engaging, and easily readable aloud by a voice assistant. The entire message should be a single, impactful paragraph that subtly blends humor/irony with motivation, without directly attributing the quote to a specific person."
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
                f"Compose a concise, unique, and creative short message for {self.user_name}, who has just finished a work session as a {self.profession} at {self.company}. "
                f"Suggest a simple 5 or 10 minute break activity like {activity}. "
                f"Keep the suggestion brief, easy to understand, and suitable for being read aloud by a voice assistant. "
                f"Focus on activities that are scientifically proven to reduce stress and enhance focus. "
                f"Add a touch of humor or irony to lighten the mood—because even serious break activities can have a fun side."
            )

        chat_completion = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": f"You are a motivational AI assistant to a {self.profession} at {self.company} named {self.user_name}. Aim for uniqueness, creativity, humour, and scientific grounding in your messages. Your messages will be read out loud to the user to format them in a way that would be easy for an apple OS voice to say out loud. "},
                {"role": "user", "content": prompt}
            ],
            model="gpt-3.5-turbo",
            temperature=0.8,
            max_tokens=200
        )
        return chat_completion.choices[0].message.content.strip()