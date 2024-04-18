import streamlit as st
import datetime
from crewai import Agent, Task, Crew, Process
from langchain_google_genai import ChatGoogleGenerativeAI
from dateutil.parser import parse as parse_date
from ics import Calendar, Event
import csv
import io

# Define Google LLM for interacting with Google Calendar
llm = ChatGoogleGenerativeAI(model="gemini-pro", verbose=True, temperature=0.6, google_api_key="AIzaSyDjITo6JpwACzQKlMCJKuBhHHK8jTQIhBg")

# Define Farmer Agent
farmer_agent = Agent(
    role='Farmer Agent',
    goal='Gather planting information from the farmer',
    backstory='An agent specialized in interacting with farmers to gather planting information.',
    verbose=True,
    allow_delegation=False,
    llm=llm
)

# Define Agronomist Agent
agronomist_agent = Agent(
    role='Agronomist Local Expert at this city',
    goal='Provide best personalized farming advice based on weather, season, and prices of the selected city',
    backstory='An expert that specialized in providing personalized farming advice based on location and crop.',
    verbose=True,
    allow_delegation=False,
    llm=llm
)

# Define Planner Agent
planner_agent = Agent(
    role='Amazing Planner Agent',
    goal='Create the most amazing planting calendar with budget and best farming practice ',
    backstory='Specialist in farm management an agronomist with decades of experience calendar based on the provided information.',
    verbose=True,
    allow_delegation=False,
    llm=llm
)

# Define Crop Suggestion Agent
crop_suggestion_agent = Agent(
    role='Crop Suggestion Agent',
    goal='Suggest alternative crops if the entered crop is out of season',
    backstory='An agent specialized in suggesting alternative crops based on seasonality and profitability.',
    verbose=True,
    allow_delegation=False,
    llm=llm
)

# Define Task for gathering planting information from the farmer
planting_info_task = Task(
    description='Gather planting information from the farmer: {plant}',
    agent=farmer_agent,
    expected_output='Planting information collected from the farmer.'
)

# Define Task for providing personalized farming advice
farming_advice_task = Task(
    description='Provide personalized farming advice for {crop} in {location} starting from {start_date}.',
    agent=agronomist_agent,
    expected_output='Personalized farming advice provided.'
)

# Define Task for generating farming calendar
farming_calendar_task = Task(
    description='Generate farming calendar for {crop} in {location} starting from {start_date}.',
    agent=planner_agent,
    expected_output='Farming calendar generated.'
)

# Define Task for advising if planting season has ended
season_check_task = Task(
    description='Check if the planting season has ended for {crop} in {location} by {current_date}.',
    agent=agronomist_agent,
    expected_output='Planting season status checked.'
)

# Define Task for suggesting alternative crops
crop_suggestion_task = Task(
    description='Suggest alternative crops if {crop} is out of season for {location} by {current_date}.',
    agent=crop_suggestion_agent,
    expected_output='Alternative crops suggested.'
)

# Define Task for displaying farming itinerary
farming_itinerary_task = Task(
    description='Display farming itinerary for {crop} in {location} starting from {start_date}.',
    agent=agronomist_agent,
    expected_output='Farming itinerary displayed.'
)

# Create a Crew for managing the farming process
farming_crew = Crew(
    agents=[farmer_agent, agronomist_agent, planner_agent, crop_suggestion_agent],
    tasks=[planting_info_task, farming_advice_task, farming_calendar_task, season_check_task, crop_suggestion_task, farming_itinerary_task],
    verbose=True,
    process=Process.sequential
)

# Function to export farming calendar to iCal (.ics) format
def export_to_ics(events):
    cal = Calendar()
    for event in events:
        e = Event()
        e.name = event['name']
        e.begin = event['start_date']
        if 'end_date' in event:
            e.end = event['end_date']
        e.description = event['description']
        cal.events.add(e)
    return cal

# Function to export farming calendar to CSV format
def export_to_csv(events):
    csv_data = io.StringIO()
    csv_writer = csv.writer(csv_data)
    csv_writer.writerow(['Task Title', 'Start Date', 'End Date (optional)', 'Description'])
    for event in events:
        csv_writer.writerow([event['name'], event['start_date'], event.get('end_date', ''), event['description']])
    return csv_data.getvalue()

# Streamlit App
st.title("AbutiSpinach: Your Farming Assistant")

# Gather planting information from the farmer
st.header("Enter Planting Information")
location = st.text_input("Location:")
crop = st.text_input("Crop:")
start_date_str = st.text_input("Start Date (YYYY-MM-DD):")

if st.button("Submit"):
    if not location or not crop or not start_date_str:
        st.error("Please fill out all fields.")
    else:
        try:
            # Validate start date format
            start_date = parse_date(start_date_str).date()
            if start_date < datetime.date.today():
                st.error("Start date must be in the future.")
            else:
                # Interpolate farmer's planting information into the tasks descriptions
                planting_info_task.interpolate_inputs({"plant": crop})
                farming_advice_task_inputs = {"crop": crop, "location": location, "start_date": start_date}
                farming_advice_task.interpolate_inputs(farming_advice_task_inputs)
                farming_calendar_task_inputs = {"crop": crop, "location": location, "start_date": start_date}
                farming_calendar_task.interpolate_inputs(farming_calendar_task_inputs)
                current_date = datetime.date.today()
                season_check_task_inputs = {"crop": crop, "location": location, "current_date": current_date}
                season_check_task.interpolate_inputs(season_check_task_inputs)
                crop_suggestion_task_inputs = {"crop": crop, "location": location, "current_date": current_date}
                crop_suggestion_task.interpolate_inputs(crop_suggestion_task_inputs)
                farming_itinerary_task_inputs = {"crop": crop, "location": location, "start_date": start_date}
                farming_itinerary_task.interpolate_inputs(farming_itinerary_task_inputs)

                # Execute the farming crew
                with st.spinner("Executing farming tasks..."):
                    events = []
                    # Execute each task sequentially
                    for task in farming_crew.tasks:
                        st.write(f"Executing task: {task.description}")
                        output = task.execute()
                        st.success("Task completed successfully!")

                        # Display agent response
                        if task.agent == agronomist_agent:
                            st.write("Agronomist Agent's Response:")
                            st.write(output)  # Display agronomist's response
                            events.append({
                                'name': 'Farming Advice',
                                'start_date': start_date,
                                'description': output
                            })
                        elif task.agent == planner_agent:
                            st.write("Planner Agent's Response:")
                            st.write(output)  # Display planner's response
                            events.append({
                                'name': 'Farming Calendar',
                                'start_date': start_date,
                                'description': output
                            })

                    # Export farming calendar to selected format
                    selected_format = st.radio("Export to:", options=["iCal (.ics)", "CSV (.csv)"])
                    if st.button("Export"):
                        try:
                            if selected_format == "iCal (.ics)":
                                cal = export_to_ics(events)
                                st.write("### Download iCal (.ics) file:")
                                st.download_button("Download", cal.to_ical(), file_name='farming_calendar.ics', mime='text/calendar')
                            elif selected_format == "CSV (.csv)":
                                csv_data = export_to_csv(events)
                                st.write("### Download CSV (.csv) file:")
                                st.download_button("Download", csv_data, file_name='farming_calendar.csv', mime='text/csv')
                        except Exception as e:
                            st.error(f"Error occurred during download: {e}")

        except ValueError:
            st.error("Invalid input. Please enter valid values.")
