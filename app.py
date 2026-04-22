import json
import requests
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Temporary in-memory storage for profiles
user_profiles = {
    "leetcode_username": None,
    "codeforces_handle": None,
    "lc_easy": None,
    "lc_medium": None,
    "lc_hard": None
}

def get_leetcode_stats():
    """Build a LeetCode stats dict from manually entered counts.
    Returns None when no counts have been saved yet."""
    easy   = user_profiles.get("lc_easy")
    medium = user_profiles.get("lc_medium")
    hard   = user_profiles.get("lc_hard")
    # Only return stats when at least one count exists
    if easy is None and medium is None and hard is None:
        return None
    easy   = easy   or 0
    medium = medium or 0
    hard   = hard   or 0
    return {
        "easy":   easy,
        "medium": medium,
        "hard":   hard,
        "total":  easy + medium + hard
    }

# Load JSON data
def load_json_data(filepath):
    with open(filepath, 'r') as file:
        return json.load(file)

def fetch_codeforces_data(handle):
    if not handle:
        return None
    try:
        url = f"https://codeforces.com/api/user.info?handles={handle}"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if data.get("status") == "OK" and data.get("result"):
            user_info = data["result"][0]
            return {
                "rating": user_info.get("rating", "N/A"),
                "max_rating": user_info.get("maxRating", "N/A"),
                "rank": user_info.get("rank", "Unrated")
            }
        return None
    except Exception:
        # Handle errors if user not found or network issues
        return None

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

def get_confidence_score():
    try:
        user_data = load_json_data('data/user_data.json') or {}
    except Exception:
        user_data = {}
        
    solved_list = user_data.get("solved", [])
    
    if not solved_list:
        return {"percentage": 0, "message": "You are 0% ready for intermediate level. Start practicing!"}
        
    diff_count = {"easy": 0, "medium": 0, "hard": 0}
    for entry in solved_list:
        diff = entry.get("difficulty", "easy")
        if diff in diff_count:
            diff_count[diff] += 1
            
    if diff_count["hard"] >= max(diff_count["easy"], diff_count["medium"]):
        next_level = "expert"
        score = diff_count["hard"] * 2 + diff_count["medium"]
        target = 30
    elif diff_count["medium"] >= max(diff_count["easy"], diff_count["hard"]):
        next_level = "advanced"
        score = diff_count["medium"] * 2 + diff_count["easy"]
        target = 20
    else:
        next_level = "intermediate"
        score = diff_count["easy"] * 1 + (diff_count["medium"] * 2)
        target = 10
        
    percentage = min(int((score / target) * 100), 100)
    
    return {
        "percentage": percentage,
        "message": f"You are {percentage}% ready for {next_level} level"
    }

# Route
@app.route('/')
def home():
    question = recommend_question()
    topic_stats = get_topic_strength()
    recommended_list = recommend_multiple_questions()
    progress_data = get_progress_data()
    confidence = get_confidence_score()
    
    # Fetch live Codeforces data if handle is connected
    cf_data = fetch_codeforces_data(user_profiles.get("codeforces_handle"))
    
    lc_stats = get_leetcode_stats()

    return render_template('dashboard.html', 
                           question=question, 
                           topic_stats=topic_stats, 
                           recommended_list=recommended_list, 
                           progress_data=progress_data, 
                           confidence=confidence,
                           user_profiles=user_profiles,
                           cf_data=cf_data,
                           lc_stats=lc_stats)

@app.route('/ask', methods=['POST'])
def ask():
    # Get user message from form
    user_message = request.form.get('message', '').lower()

    # Load topic strength to personalize the response
    topic_stats = get_topic_strength()
    total_solved = sum(topic_stats.values())

    # --- Context: No data (brand new user) ---
    if total_solved == 0:
        ai_response = "Start with arrays and easy problems before moving ahead."

    # --- Context: User has data, check keyword + strength ---
    elif 'dp' in user_message:
        if topic_stats.get('dp', 0) >= 50:
            ai_response = "You're doing well in DP! Try hard problems like 'Edit Distance' or 'Burst Balloons'."
        else:
            ai_response = "You are weak in DP. Focus on recursion and memoization before tackling harder problems."

    elif 'graph' in user_message:
        if topic_stats.get('graph', 0) >= 50:
            ai_response = "Strong graph skills! Challenge yourself with Dijkstra's algorithm or topological sort."
        else:
            ai_response = "Practice graph basics: BFS, DFS, and cycle detection first."

    elif 'array' in user_message:
        if topic_stats.get('array', 0) >= 50:
            ai_response = "Arrays are your strength! Move on to sliding window and two-pointer hard problems."
        else:
            ai_response = "Start with array basics: two-sum, max subarray, and prefix sums."

    elif 'next' in user_message:
        # Suggest based on the weakest topic
        weakest = min(topic_stats, key=lambda t: topic_stats[t])
        ai_response = f"Focus on your weakest topic ({weakest}) and gradually increase difficulty."

    else:
        # Generic fallback with a useful nudge based on current progress
        weakest = min(topic_stats, key=lambda t: topic_stats[t])
        ai_response = f"You can ask me about 'dp', 'graph', 'array', or 'next'. Tip: you need more practice in {weakest}!"

    question = recommend_question()
    recommended_list = recommend_multiple_questions()
    progress_data = get_progress_data()
    confidence = get_confidence_score()
    
    # Fetch live Codeforces data if handle is connected
    cf_data = fetch_codeforces_data(user_profiles.get("codeforces_handle"))

    lc_stats = get_leetcode_stats()

    return render_template('dashboard.html',
                           question=question,
                           topic_stats=topic_stats,
                           recommended_list=recommended_list,
                           progress_data=progress_data,
                           confidence=confidence,
                           ai_response=ai_response,
                           user_profiles=user_profiles,
                           cf_data=cf_data,
                           lc_stats=lc_stats)

@app.route('/profile', methods=['POST'])
def profile():
    lc = request.form.get('leetcode_username', '')
    cf = request.form.get('codeforces_handle', '')

    user_profiles["leetcode_username"] = lc.strip() if lc and lc.strip() else None
    user_profiles["codeforces_handle"] = cf.strip() if cf and cf.strip() else None

    def parse_count(field):
        """Return int if a valid non-negative number was submitted, else None."""
        val = request.form.get(field, '').strip()
        if val.isdigit():
            return int(val)
        return None

    user_profiles["lc_easy"]   = parse_count('lc_easy')
    user_profiles["lc_medium"] = parse_count('lc_medium')
    user_profiles["lc_hard"]   = parse_count('lc_hard')

    return redirect(url_for('home'))

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)