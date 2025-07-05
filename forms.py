from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class BlogPostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(max=200)])
    category = SelectField('Category', choices=[
        ('Technology', 'Technology'),
        ('Hardware', 'Hardware'),
        ('Biking', 'Biking'),
        ('Cybersecurity', 'Cybersecurity'),
        ('Personal', 'Personal'),
        ('Tutorial', 'Tutorial')
    ], validators=[DataRequired()])
    excerpt = TextAreaField('Excerpt (optional)', validators=[Length(max=300)])
    content = TextAreaField('Content', validators=[DataRequired()],
                           render_kw={"rows": 15})
    submit = SubmitField('Save Post')