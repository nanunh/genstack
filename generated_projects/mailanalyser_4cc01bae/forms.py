from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, SelectField, HiddenField
from wtforms.validators import DataRequired, Email

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    server = StringField('IMAP Server', validators=[DataRequired()], default='imap.gmail.com')
    port = IntegerField('Port', validators=[DataRequired()], default=993)

class AnalysisRequestForm(FlaskForm):
    email_id = HiddenField('Email ID', validators=[DataRequired()])
    analysis_type = SelectField('Analysis Type', choices=[
        ('summary', 'Summarize Email'),
        ('sentiment', 'Analyze Sentiment'),
        ('action_items', 'Extract Action Items'),
        ('key_points', 'Extract Key Points'),
        ('categorize', 'Categorize Email'),
        ('priority', 'Determine Priority'),
        ('comprehensive', 'Comprehensive Analysis')
    ], validators=[DataRequired()])
