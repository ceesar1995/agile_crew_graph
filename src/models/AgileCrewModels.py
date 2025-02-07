from typing import List

from pydantic.v1 import BaseModel, Field


class BaseTask(BaseModel):
    title: str = Field(
        description="Title of the task, should be a significant one, descriptive enough to understand it, e.g. Create new user"
    )
    description: str = Field(
        description="Detailed description of the task, should contain all necessary information to understand the task"
    )


class ListOfTasks(BaseModel):
    tasks: List[BaseTask] = Field(
        description="List of tasks to be created"
    )

    def __str__(self):
        return "\n".join(f"- Task '{task.title}'\n\tDescription: {task.description}" for task in self.tasks)

class ListBaseTasksWithReasoning(BaseModel):
    """List of tasks to be created in the expected format."""
    reasoning: str = Field(
        description="Conceptual solution about the tasks creation."
    )
    tasks_draft: str = Field(
        description="Detailed draft of the tasks to create."
    )
    tasks: List[BaseTask] = Field(
        description="List of tasks to be created"
    )

class ListOfAcceptanceCriteria(BaseModel):
    acceptance_criteria: List[str] = Field(
        description="List of acceptance criteria for the user story"
    )

    def __str__(self):
        return "\n".join(f"-  {ac}" for ac in self.acceptance_criteria)

class BaseAcceptanceCriteriaWithReasoning(BaseModel):
    """List of acceptance criteria to be created in the expected format."""
    reasoning: str = Field(
        description="Conceptual solution about the acceptance criteria creation."
    )
    acceptance_criteria_draft: str = Field(
        description="Detailed draft of the acceptance criteria to create."
    )
    acceptance_criteria: List[str] = Field(
        description="List of acceptance criteria for the user story"
    )

class BaseUserStory(BaseModel):
    title: str = Field(
        description="Title of the user story, follow the format: As a <type of user>, I want <some goal> so that <some reason>."
    )
    description: str = Field(
        description="Detailed description of the user story, should contain all necessary information to understand the user story."
    )
    processed: bool = Field(
        description="Flag to indicate if the user story has been processed", default=False
    )

    def __str__(self):
        return f"- User Story '{self.title}'\n\tDescription: {self.description}"


class ListOfUserStories(BaseModel):
    user_stories: List[BaseUserStory] = Field(
        description="List of user stories to be created"
    )

    def __str__(self):
        return "\n".join(str(us) for us in self.user_stories)


class ListBaseUserStoryWithReasoning(BaseModel):
    """List of user stories to be created in the expected format."""
    reasoning: str = Field(
        description="Conceptual solution about the user stories creation."
    )
    user_stories_draft: str = Field(
        description="Detailed draft of the user stories to create."
    )
    user_stories: List[BaseUserStory] = Field(
        description="List of user stories to be created"
    )
class BaseFeature(BaseModel):
    title: str = Field(
        description="Title of the feature, should be a significant one, descriptive enough to understand it, e.g. Create new user"
    )
    description: str = Field(
        description="Detailed description of the feature, should contain all necessary information to understand the feature"
    )


class Task(BaseTask):
    type: str = "Task"


class UserStory(BaseUserStory):
    story_points: int | None = Field(
        default=None,
        description="Story points are used to estimate the effort required to complete a task, e.g. 1, 2, 3, 5, 8, 13.",
    )
    acceptance_criteria: list[str] | None = Field(
        description="Acceptance criteria are a set of conditions that a software product must satisfy to be accepted by a user.",
    )
    type: str = "User Story"
    tasks: list[Task] | None = Field(
        description="List of tasks that are part of the user story"
    )

    def __str__(self):
        return f"\t\tUser Story '{self.title}'\n\t\t\tDescription: {self.description}\n\t\t\tAcceptance Criteria:\n\t\t\t" + "\n\t\t\t".join(f"-  {ac}" for ac in self.acceptance_criteria) +'\n\t\t\tTasks:' + "".join(f"\n\t\t\t- Task '{task.title}'\n\t\t\t\tDescription: {task.description}" for task in self.tasks)


class Feature(BaseFeature):
    type: str = "Feature"
    user_stories: list[UserStory] = Field(
        default=None, description="List of user stories that are part of the feature"
    )

    def __str__(self):
        return f"Feature '{self.title}'\n\tDescription: {self.description}\n\tUser Stories:\n" \
               "" + "\n".join(f"{str(us)}" for us in self.user_stories)


class FeedbackOutput(BaseModel):
    """Feedback provided on the work done."""
    feedback: str = Field(description="Feedback provided on the work done.")
    needs_review: bool = Field(description="Flag to indicate if the work needs to be reviewed with the feedback "
                                           "provided. Set to True if review is needed.", default=False)

    def __str__(self):
        return f"Feedback: {self.feedback}"


class AgileWorkItems(BaseModel):
    items: List[Feature] = Field(description="Feature work items to be created")