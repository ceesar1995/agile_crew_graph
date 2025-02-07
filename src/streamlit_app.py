import json
import os
import uuid

import streamlit as st
from bluesheperd.core.project import AzureProject

from AgileGraph import AgileCrewGraph
from Utils import save_to_ado
from models.AgileCrewModels import AgileWorkItems
from models.AgileCrewModels import Feature, Task

agile_crew = AgileCrewGraph()
st.set_page_config(page_title="Agile LLM Graph Team")
st.title('Agile LLM Graph Team')


@st.dialog("Feature", width="large")
def create_feature(feature: Feature, popup: bool = False):
    feature_ui(feature, popup=popup)


# Define the UI for the feature model
def feature_ui(feature: Feature, popup: bool = False):
    with st.container(border=True):
        editing_disabled = not popup
        feature.title = st.text_input("Title", feature.title, disabled=editing_disabled, key=uuid.uuid4())
        feature.description = st.text_area("Description", value=feature.description, disabled=editing_disabled,
                                           key=uuid.uuid4())
        st.write("User Stories")

        def delete_user_story(user_story):
            feature.user_stories.remove(user_story)
            st.rerun()

        for user_story in feature.user_stories:
            with st.expander(f"{user_story.title}"):
                user_story.title = st.text_input("Title", value=user_story.title, disabled=editing_disabled,
                                                 key=uuid.uuid4())
                user_story.description = st.text_area("Description", value=user_story.description,
                                                      disabled=editing_disabled, key=uuid.uuid4())
                st.write("Acceptance Criteria")
                st.divider()
                new_criteria = []
                for idx, acceptance_criteria in enumerate(user_story.acceptance_criteria):
                    new_criteria.append(st.text_area(f"#{idx}", value=acceptance_criteria, disabled=editing_disabled,
                                                     key=uuid.uuid4()))
                    # Insert divider except for the last acceptance criteria
                    if idx < len(user_story.acceptance_criteria) - 1:
                        st.divider()
                user_story.acceptance_criteria = new_criteria
                st.write("Tasks")
                st.divider()
                new_tasks = []
                for idx, task in enumerate(user_story.tasks):
                    new_tasks.append(Task(
                        title=st.text_input("Title", value=task.title, disabled=editing_disabled,
                                            key=uuid.uuid4()),
                        description=st.text_area("Description", value=task.description,
                                                 disabled=editing_disabled, key=uuid.uuid4())
                    ))
                    # Insert divider except for the last task
                    if idx < len(user_story.tasks) - 1:
                        st.divider()
                user_story.tasks = new_tasks
            st.button("Delete User Story", key=uuid.uuid4(), on_click=delete_user_story, args=(user_story,),
                      disabled=editing_disabled)
        if not ado_pat or not target_org_url or not project_name:
            st.warning('Please enter your Azure DevOps PAT, Org URL, and Project Name!', icon='⚠')
        if popup:
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button('Submit Feature to Azure DevOps',
                             use_container_width=True) \
                        and ado_pat and target_org_url and project_name:
                    with st.spinner('Creating feature in Azure Dev Ops...'):
                        try:
                            # Call Azure DevOps API to create feature
                            ado_project = create_ado_project(target_org_url, ado_pat, project_name)
                            work_item = AgileWorkItems(items=[feature])
                            print(work_item.json())
                            save_to_ado(work_item.json(), ado_project)
                        except Exception as e:
                            st.error(f'Error creating feature: {e}')
                            st.rerun()
                    st.session_state.feature[str(uuid.uuid4())] = feature
                    st.toast('Feature created successfully!')
                    st.rerun()
            with col2:
                if st.button('Save Feature', use_container_width=True):
                    st.session_state.feature[str(uuid.uuid4())] = feature
                    st.toast('Feature saved successfully!')
                    st.rerun()

        else:
            edit = st.button("Edit and Submit to Azure DevOps")
            if edit:
                create_feature(feature, popup=True)


def get_feature_title(key: str):
    return st.session_state.feature[key].title


def create_ado_project(target_organization_url: str, personal_access_token: str, project_name: str) -> AzureProject:
    project = AzureProject(
        organization_url=target_organization_url,
        project_name=project_name,
        pat=personal_access_token,
    )
    ado_project = project.connect()
    return ado_project


# Initialize the feature dictionary in the session state
if 'feature' not in st.session_state:
    st.session_state.feature = {}

# Sidebar components
with st.sidebar:
    openai_api_key = st.text_input('OpenAI API Key')
    ado_pat = st.text_input('Azure DevOps PAT')
    target_org_url = st.text_input('Azure DevOps Org URL')
    project_name = st.text_input('Azure DevOps Project Name')
    with st.form("my-form", clear_on_submit=True):
        file = st.file_uploader("Feature uploader", type=['json'])
        submitted = st.form_submit_button("Upload!")

    if submitted and file is not None:
        st.toast("Uploaded succesfully!")
        try:
            feature = Feature(**json.loads(file.getvalue().decode("utf-8")))
            create_feature(feature, popup=True)
        except Exception as e:
            st.error(f'Error creating feature: {e}')
    feature_selected = st.selectbox('Features created', [key for key in st.session_state.feature.keys()],
                                    index=None, format_func=get_feature_title)
with st.form('my_form'):
    feature_description = st.text_area('Feature description:', placeholder='Enter the feature description here')
    project_context = st.text_area('Project context:',
                                   placeholder='Enter some information about the project context here')
    submitted = st.form_submit_button('Submit')

    if not openai_api_key:
        st.warning('Please enter your OpenAI API key!', icon='⚠')
    if submitted and openai_api_key:
        os.environ['AZURE_OPENAI_API_KEY'] = openai_api_key
        with st.spinner('Agile LLM is creating the feature...'):
            try:
                feature = agile_crew.invoke_graph(feature_description, project_context)
                create_feature(feature, popup=True)
            except Exception as e:
                st.error(f'Error creating feature: {e}')

# Display the selected feature from the selectbox in the sidebar
if feature_selected:
    feature_ui(st.session_state.feature[feature_selected])
    st.sidebar.download_button('Download Feature', st.session_state.feature[feature_selected].json(),
                               f'feature-{feature_selected}.json')
