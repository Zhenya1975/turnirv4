from flask import Blueprint, render_template, flash, request, jsonify, redirect, url_for, abort
from sqlalchemy import desc
from ..models.models import ParticipantsDB, FightsDB, CompetitionsDB, BacklogDB, RegistrationsDB
from ..extensions import db
import csv

home = Blueprint('home', __name__, template_folder='templates')


@home.route('/')
def home_view():
    return redirect(url_for('home.competition_start'))


@home.route('/fill_fighters')
def fill_fighters():
  with open('fighters.csv', encoding='utf8') as csvfile:
    fighters_csv_list = csv.reader(csvfile)
    for row in fighters_csv_list:
      new_fighter = ParticipantsDB(participant_first_name=row[0], participant_last_name=row[1])
      db.session.add(new_fighter)
      try:
          db.session.commit()
          print("Бойцы импортированы в ParticipantsDB")
      except Exception as e:
          print("Не получилось импортировать бойцов. Ошибка: ", e)
          db.session.rollback()
  return "результат импорта - в принт"

  

def fight_create_func(competition_id, round_number, final_status):
  competition_id = competition_id
  round_number = round_number
  final_status = final_status
  backlog_data = BacklogDB.query.filter_by(competition_id=competition_id, round_number=round_number).all()
  red_fighter_id = backlog_data[0].fighter_id
  blue_fighter_id = backlog_data[1].fighter_id
  new_fight = FightsDB(competition_id=competition_id, round_number=round_number, red_fighter_id=red_fighter_id,
                       blue_fighter_id=blue_fighter_id, final_status=final_status)
  db.session.add(new_fight)
  
  try:
      db.session.commit()
      print("создан новый бой в круге №", round_number, ". id бойцов:", red_fighter_id, " и ", blue_fighter_id)

  except Exception as e:
      print("не получилось создать новый бой. Ошибка:  ", e)
      db.session.rollback()
    
  return round_number

      ################################################################

def delete_backlog_records(competition_id, round_number):
  competition_id = competition_id
  round_number = round_number
  # удаляем из бэклога записи с бойцами из созданннного боя
  last_created_fight = FightsDB.query.filter_by(competition_id=competition_id, round_number=round_number).order_by(desc(FightsDB.fight_id)).first()
   # удаляем записи из бэклога бойцов, которые зашли в бой
  backlog_record_to_delete_red = BacklogDB.query.filter_by(competition_id=competition_id, round_number=round_number, fighter_id=last_created_fight.red_fighter_id).order_by(desc(BacklogDB.fighter_id)).first()
  if backlog_record_to_delete_red is None:
      abort(404, description="No backlog record was Found with the given ID")
  else:
      db.session.delete(backlog_record_to_delete_red)
  backlog_record_to_delete_blue = BacklogDB.query.filter_by(competition_id=competition_id, round_number=round_number, fighter_id=last_created_fight.blue_fighter_id).order_by(desc(BacklogDB.fighter_id)).first()
  if backlog_record_to_delete_blue is None:
      abort(404, description="No backlog record was Found with the given ID")
  else:
      db.session.delete(backlog_record_to_delete_blue)
  try:
    db.session.commit()
    print("удалены записи из бэклога. red_fighter: ", backlog_record_to_delete_red, ". blue_fighter: ", backlog_record_to_delete_blue)
  except Exception as e:
    print("Не удалось удалить записи из бэклога", e)
    db.session.rollback()
  ########################################################

@home.route('/competition_start/')
def competition_start():
    # создаем первый бой
    # fight_create_func(1)
    # last_created_fight = FightsDB.query.order_by(desc(FightsDB.fight_id)).first()
    return render_template('competition_start.html')

@home.route('/competition_create_new/')
def competition_create_new():
    #  создаем новое соревнование
    new_competition = CompetitionsDB()
    db.session.add(new_competition)

    try:
        db.session.commit()
        created_competition_data = CompetitionsDB.query.order_by(desc(CompetitionsDB.competition_id)).first()
        competition_id = created_competition_data.competition_id
        # создаем записи регистраций на созданное соревнование
        participant_data = ParticipantsDB.query.all()
        for participant in participant_data:
          new_registration = RegistrationsDB(participant_id = participant.participant_id, competition_id = competition_id, activity_status = 1)
          db.session.add(new_registration)
          try:
            db.session.commit()
          except Exception as e:
            print("Не удалось создать запись в регистрациях", e)
            db.session.rollback()
        
        # помещаем всех бойцов в бэклог
        # participants_data = ParticipantsDB.query.all()
        regs_data = RegistrationsDB.query.filter_by(competition_id = competition_id).all()
        for registration in regs_data:
          reg_id = registration.reg_id
          new_backlog_record = BacklogDB(fighter_id=reg_id, competition_id=competition_id, round_number=1)
          db.session.add(new_backlog_record)
          try:
            db.session.commit()
          except Exception as e:
            print("Не удалось создать запись в бэклоге", e)
            db.session.rollback()
        
        # проверяем ситуацию в бэклоге в текущем и следующем раунде
        next_round_backlog_data = BacklogDB.query.filter_by(competition_id=competition_id, round_number=2).all()
        print("длина бэклога следующего раунда: ", len(next_round_backlog_data))
        # ситуация №1 в текущем раунде нет боев, а в следующем раунде есть два бойца в бэклоге. Значит следующий бой будет финальным. 
        current_backlog_data = BacklogDB.query.filter_by(competition_id=competition_id, round_number=1).all()
        if len(current_backlog_data) == 0 and len(next_round_backlog_data) == 2:
          print("следующий бой будет финальным")
          current_round_number = 2
          # создаем новый бой - финальный
          final_status='final'
          fight_create_func(competition_id, current_round_number, final_status)
          # удаляем из бэклога записи с бойцами
          delete_backlog_records(competition_id, current_round_number)
        # ситуация №2. Если в текущем раунде два бойца, а в следующем ноль. это тоже будет финальный бой
        elif len(current_backlog_data) == 2 and len(next_round_backlog_data) == 0:
          print("следующий бой будет финальным")
          current_round_number = 1
          final_status='final'
          fight_create_func(competition_id, current_round_number, final_status)
          # удаляем из бэклога записи с бойцами
          delete_backlog_records(competition_id, current_round_number)
       
        else:  
          fight_create_func(competition_id, 1, 'not')
          # удаляем из бэклога записи с созданным боем
          last_created_fight = FightsDB.query.filter_by(competition_id=competition_id).order_by(desc(FightsDB.fight_id)).first()
          # удаляем записи из бэклога бойцов, которые зашли в бой
          delete_backlog_records(last_created_fight.competition_id, 1)  

        
        return redirect(url_for('home.competition_view', competition_id=competition_id))

    except Exception as e:
        print("Не удалось создать соревнование", e)
        db.session.rollback()
        return render_template('competition_start.html')

@home.route('/test/<int:fight_id>')
def test(fight_id):
  print("fight_id_test", fight_id)
  return "testtt"

@home.route('/competition/<int:competition_id>')
def competition_view(competition_id):
    competition_id = competition_id
    # round_number = fight_create_func(round_number_prev)
    last_created_fight = FightsDB.query.filter_by(competition_id=competition_id).order_by(desc(FightsDB.fight_id)).first()
    print("id последнего созданного боя", last_created_fight.fight_id)
    return render_template("competition.html", fight_data=last_created_fight)


@home.route('/competition_finish/<int:fight_id>')
def finish_red(fight_id):
  fight_data = FightsDB.query.get(fight_id)
  winner_red_fighter_id = fight_data.red_fighter_id
  
  winner_data = ParticipantsDB.query.get(winner_red_fighter_id)
  print("winner_data", winner_data)
  return render_template("finish.html", winner_data=winner_data)

@home.route('/ajaxfile_red_fighter', methods=["POST", "GET"])
def ajaxfile_red_fighter():
    if request.method == 'POST':
      fight_id = request.form['fight_id']
      current_fight_data = FightsDB.query.get(fight_id)
      competition_id = current_fight_data.competition_id
      current_round_number = current_fight_data.round_number
      print("fight_id после нажатия ajaxfile_red_fighter", fight_id)
      print("competition_id после нажатия ajaxfile_red_fighter", competition_id)
      print("current_round_number ajaxfile_red_fighter", current_round_number)

      # выводим из игры синего бойца
      print("на удаление ", current_fight_data.blue_fighter.participant_last_name)
      current_fight_data.blue_fighter.activity_status = 0
      try:
        db.session.commit()
      except Exception as e:
        print("Не удалось вывести из игры синего бойца", e)
        db.session.rollback()
      # добавляем в бэклог в следующий круг новую запись с победившим
      new_backlog_record = BacklogDB(fighter_id=current_fight_data.red_fighter_id, competition_id=competition_id, round_number=current_round_number+1)
      db.session.add(new_backlog_record)
      try:
        db.session.commit()
        print("добавлена запись в бэклог с бойцом id: ", current_fight_data.red_fighter_id, " в раунд: ", current_round_number+1)
      except Exception as e:
        print("не удалось добавить запись с победившим в бэклог", e)
        db.session.rollback()
      
      # проверяем ситуацию в бэклоге в текущем и следующем раунде
      next_round_backlog_data = BacklogDB.query.filter_by(competition_id=competition_id, round_number=current_round_number+1).all()
      print("длина бэклога следующего раунда: ", len(next_round_backlog_data))
      # ситуация №1 в текущем раунде нет боев, а в следующем раунде есть два бойца в бэклоге. Значит следующий бой будет финальным. 
      current_backlog_data = BacklogDB.query.filter_by(competition_id=competition_id, round_number=current_round_number).all()
      if len(current_backlog_data) == 0 and len(next_round_backlog_data) == 2:
        print("следующий бой будет финальным")
        current_round_number = current_round_number+1
        # создаем новый бой - финальный
        final_status='final'
        fight_create_func(competition_id, current_round_number, final_status)
        # удаляем из бэклога записи с бойцами
        delete_backlog_records(competition_id, current_round_number)
      # ситуация №2. Если в текущем раунде два бойца, а в следующем ноль. это тоже будет финальный бой
      if len(current_backlog_data) == 2 and len(next_round_backlog_data) == 0:
        print("следующий бой будет финальным")
        
        # создаем новый бой - финальный
        final_status='final'
        fight_create_func(competition_id, current_round_number, final_status)
        # удаляем из бэклога записи с бойцами
        delete_backlog_records(competition_id, current_round_number)
        
        # backlog_data = BacklogDB.query.filter_by(competition_id=competition_id, round_number=current_round_number).all()
      # print("длина бэклога в раунде ", current_round_number, ": ", len(backlog_data))
      # if len(backlog_data)>1:
      #   print('длина бэклога - больше одного: ', len(backlog_data))
      #   fight_create_func(competition_id, current_round_number)
      #   # удаляем из бэклога записи с бойцами
      #   delete_backlog_records(competition_id, current_round_number)

      # elif len(backlog_data)==1:
      #   # получаем данные бойца из следующего круга
      #   try:
      #     next_round_fighter_data = BacklogDB.query.filter_by(competition_id=competition_id, round_number=current_round_number+1).first()
      #   except Exception as e:
      #     print("не удалось получить данные бойца из следующего раунда", e)
      #   # проверяем на случай если это один и тот же боец
      #   current_round_fighter_data = BacklogDB.query.filter_by(competition_id=competition_id, round_number=current_round_number).first()
      #   if next_round_fighter_data.fighter_id != current_round_fighter_data.fighter_id:   
      #     next_round_fighter_data.round_number = current_round_number
      #     try:
      #       db.session.commit()
      #       print("изменили данные бойца из следующего круга")
      #     except Exception as e:
      #       print("не удалось переписать номер круга в записи бойца из следующего круга", e)
      #       db.session.rollback()
      #     fight_create_func(competition_id, current_round_number)
      #     # удаляем из бэклога записи с бойцами
      #     delete_backlog_records(competition_id, current_round_number)
      #   else:
      #     print("один и тот же боец в текущем и следующем раунде финиш")

      
      # elif len(backlog_data)==0:
      #   # проверяем длину бэклога следующего раунда
      #   next_round_backlog_data = BacklogDB.query.filter_by(competition_id=competition_id, round_number=current_round_number+1).all()
      #   print("длина бэклога следующего раунда: ", len(next_round_backlog_data))
      #   if len(next_round_backlog_data)>=2:
      #     current_round_number = current_round_number+1
      #     print("current_round_number", current_round_number)
      #     fight_create_func(competition_id, current_round_number)
      #     # удаляем из бэклога записи с бойцами
      #     delete_backlog_records(competition_id, current_round_number)
            
      #   else:
      #     # финал
      #     print('финал')
          
  

      last_created_fight = FightsDB.query.filter_by(competition_id=competition_id, round_number=current_round_number).order_by(desc(FightsDB.fight_id)).first()
      print("last_created_fight_id", last_created_fight.fight_id)
      return jsonify(
          {'htmlresponsered': render_template('response_red_fighter_div.html', fight_data=last_created_fight),
           'htmlresponseblue': render_template('response_blue_fighter_div.html', fight_data=last_created_fight),
           'htmlresponsetitle': render_template('response_title_div.html', fight_data=last_created_fight),
           })  
    
      
        
        
         
        
        
          
        
        
