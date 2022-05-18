from ..extensions import db


class ParticipantsDB(db.Model):
    participant_id = db.Column(db.Integer, primary_key=True)
    participant_first_name = db.Column(db.String)
    participant_last_name = db.Column(db.String)
    activity_status = db.Column(db.Integer, default=1)
    red_fighter = db.relationship('FightsDB', backref='red_fighter', foreign_keys="[FightsDB.red_fighter_id]")
    blue_fighter = db.relationship('FightsDB', backref='blue_fighter', foreign_keys="[FightsDB.blue_fighter_id]")

class CompetitionsDB(db.Model):
    competition_id = db.Column(db.Integer, primary_key=True)
    fights = db.relationship('FightsDB', backref='competition')


class FightsDB(db.Model):
    fight_id = db.Column(db.Integer, primary_key=True)
    competition_id = db.Column(db.Integer, db.ForeignKey('competitionsDB.competition_id'))
    round_number = db.Column(db.Integer)
    red_fighter_id = db.Column(db.Integer, db.ForeignKey('participantsDB.participant_id'))
    blue_fighter_id = db.Column(db.Integer, db.ForeignKey('participantsDB.participant_id'))
    fight_winner_id = db.Column(db.Integer, default=0)
    final_status = db.Column(db.String, default='not')

class BacklogDB(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fighter_id = db.Column(db.Integer, db.ForeignKey('participantsDB.participant_id'))
    competition_id = db.Column(db.Integer, db.ForeignKey('competitionsDB.competition_id'))
    round_number = db.Column(db.Integer)


