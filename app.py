import json
from flask import Flask, render_template, request

app = Flask(__name__)

# Load JSON data
def load_json_data(filepath):
    with open(filepath, 'r') as file:
        return json.load(file)

# Smart recommendation based on user's weakest topic and difficulty
def recommend_question():
    try:
        # Load questions and user's solved history safely
        questions = load_json_data('data/questions.json') or []
        user_data = load_json_data('data/user_data.json') or {}
    except Exception:
        # Prevent crash if files are missing or malformed
        questions = []
        user_data = {}

    # If absolutely no questions exist, return a guaranteed default to ensure we ALWAYS return a valid question
    if not questions:
        return {
            "name": "Two Sum",
            "topic": "array",
            "difficulty": "easy",
            "reason": "Let's start with a classic default problem!",
            "link": "https://leetcode.com/problems/two-sum/"
        }

    # Count how many problems the user solved per topic and difficulty
    topic_count = {"array": 0, "graph": 0, "dp": 0}
    diff_count = {"easy": 0, "medium": 0, "hard": 0}

    solved_list = user_data.get("solved", [])
    for entry in solved_list:
        topic = entry.get("topic")
        diff = entry.get("difficulty")
        if topic in topic_count:
            topic_count[topic] += 1
        if diff in diff_count:
            diff_count[diff] += 1

    # Find the topic with the lowest solved count (weakest topic)
    weakest_topic = min(topic_count, key=lambda t: topic_count[t])

    # Determine target difficulty based on mostly solved
    total_solved = sum(diff_count.values())
    if total_solved == 0:
        target_diffs = ["easy"]
        prog_msg = ""
    else:
        most_solved = max(diff_count, key=lambda d: diff_count[d])
        if most_solved == "easy":
            target_diffs = ["medium"]
            prog_msg = " and ready to move from easy to medium level"
        elif most_solved == "medium":
            target_diffs = ["medium", "hard"]
            prog_msg = " and ready for medium or hard level problems"
        else:
            target_diffs = ["hard"]
            prog_msg = " and tackling hard level problems"

    # Primary attempt: Match BOTH weakest topic and target difficulty progression
    for question in questions:
        if question.get("topic") == weakest_topic and question.get("difficulty") in target_diffs:
            result = dict(question)
            result["reason"] = f"You are weak in {weakest_topic}{prog_msg}."
            return result

    # Fallback 1: Match same topic, any difficulty
    # If we couldn't find a question for the specific topic + difficulty combo,
    # we still want to prioritize their weakest topic.
    for question in questions:
        if question.get("topic") == weakest_topic:
            result = dict(question)
            result["reason"] = f"You are weak in {weakest_topic}."
            return result

    # Fallback 2: Any available question
    # If we completely failed to find any question for their weakest topic,
    # we just return the first question available so the app never crashes.
    result = dict(questions[0])
    result["reason"] = "This is a great practice problem to get started!"
    return result

def get_topic_strength():
    # 1. Load user data from data/user_data.json safely
    try:
        user_data = load_json_data('data/user_data.json') or {}
    except Exception:
        user_data = {}

    # 2. Extract solved problems list
    solved_list = user_data.get("solved", [])

    # 3. Count how many problems are solved per topic (array, graph, dp)
    topic_count = {"array": 0, "graph": 0, "dp": 0}
    total_solved = 0
    
    for entry in solved_list:
        topic = entry.get("topic")
        if topic in topic_count:
            topic_count[topic] += 1
            total_solved += 1

    # 4. Calculate percentage for each topic
    topic_strength = {}
    for topic, count in topic_count.items():
        # If total_solved is 0, return 0 for all topics
        if total_solved == 0:
            topic_strength[topic] = 0
        else:
            # (topic_count / total_solved) * 100
            topic_strength[topic] = int((count / total_solved) * 100)

    # 5. Return the resulting dictionary
    return topic_strength

def recommend_multiple_questions():
    # 1. Get the primary recommendation using existing logic (weakest topic + next difficulty)
    q1 = recommend_question()
    
    if not q1:
        return []
        
    recommended = [q1]
    recommended_names = [q1.get("name")]
    
    # Safely load all questions to find the remaining two
    try:
        questions = load_json_data('data/questions.json') or []
    except Exception:
        questions = []
        
    # Get topic strengths to find weakest and second weakest topics
    topic_stats = get_topic_strength()
    
    # Sort topics by their strength to easily find 1st and 2nd weakest
    sorted_topics = sorted(topic_stats.keys(), key=lambda t: topic_stats[t])
    
    weakest_topic = sorted_topics[0] if len(sorted_topics) > 0 else "array"
    second_weakest_topic = sorted_topics[1] if len(sorted_topics) > 1 else weakest_topic

    # 2. Find a second question from the SAME weakest topic
    for q in questions:
        # Avoid duplicate questions by checking the name
        if q.get("name") not in recommended_names and q.get("topic") == weakest_topic:
            q2 = dict(q)
            q2["reason"] = f"Another problem to strengthen your weakest topic: {weakest_topic}."
            recommended.append(q2)
            recommended_names.append(q2.get("name"))
            break
            
    # 3. Find a third question from the SECOND weakest topic
    for q in questions:
        # Avoid duplicate questions by checking the name
        if q.get("name") not in recommended_names and q.get("topic") == second_weakest_topic:
            q3 = dict(q)
            q3["reason"] = f"Let's also practice your second weakest topic: {second_weakest_topic}."
            recommended.append(q3)
            recommended_names.append(q3.get("name"))
            break
            
    # 4. Fallback: If we don't have exactly 3 questions yet, fill with any available non-duplicates
    for q in questions:
        if len(recommended) >= 3:
            break
        if q.get("name") not in recommended_names:
            extra_q = dict(q)
            extra_q["reason"] = "A great extra practice problem."
            recommended.append(extra_q)
            recommended_names.append(extra_q.get("name"))
            
    return recommended

def get_progress_data():
    # Load user data safely
    try:
        user_data = load_json_data('data/user_data.json') or {}
    except Exception:
        user_data = {}
        
    history = user_data.get("history", [])
    
    labels = []
    values = []
    
    # Extract day labels and problem counts
    for entry in history:
        if "day" in entry and "count" in entry:
            labels.append(entry["day"])
            values.append(entry["count"])
            
    return {
        "labels": labels,
        "values": values
    }

# Route
@app.route('/')
def home():
    question = recommend_question()
    topic_stats = get_topic_strength()
    recommended_list = recommend_multiple_questions()
    progress_data = get_progress_data()
    return render_template('dashboard.html', question=question, topic_stats=topic_stats, recommended_list=recommended_list, progress_data=progress_data)

@app.route('/ask', methods=['POST'])
def ask():
    # Get user message from form
    user_message = request.form.get('message', '').lower()
    
    # Simple rule-based response logic
    if 'dp' in user_message:
        chat_response = "You are weak in DP, focus on recursion and memoization."
    elif 'next' in user_message:
        chat_response = "Focus on your weakest topic and gradually increase difficulty."
    else:
        chat_response = "I'm here to help! Ask me about topics like 'dp' or your 'next' steps."
    
    # Reload all dashboard data
    question = recommend_question()
    topic_stats = get_topic_strength()
    recommended_list = recommend_multiple_questions()
    progress_data = get_progress_data()
    
    return render_template('dashboard.html', 
                           question=question, 
                           topic_stats=topic_stats, 
                           recommended_list=recommended_list, 
                           progress_data=progress_data,
                           ai_response=chat_response)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)