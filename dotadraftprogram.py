import json
from operator import truediv
import requests
from datetime import datetime
from pathlib import Path

#Obtain a key from https://steamcommunity.com/dev/apikey
steam_api_key = "INSERT API KEY WITHIN QUOTATIONS HERE"

teamid = input("Enter Team ID as number. Ex: Evil Geniuses would be '39': ")
numberOfMatches = int(input("Enter number of matches on this printout. Each Page fits 6 drafts. Default Value is 12: ") or "12")

def get_imageDict():
    """
    Creates dictionary of hero images and hero names. Requires API Key
    """
    r = requests.get(f"https://api.steampowered.com/IEconDOTA2_570/GetHeroes/v0001/?key={steam_api_key}&language=en")
    if r.ok:
        print("Steam API Request OK!")
    else:
        raise Exception("Problem with Steam API Request. Check your API key.")

    b = json.loads(r.text)['result']['heroes']
    
    hero_image_dict = {}
    for hero in b:
        hero_image_dict[hero['id']] = {'hero': hero['localized_name'] , 
                                    'vert':  "http://cdn.dota2.com/apps/dota2/images/heroes/" + hero['name'][14::] + "_vert.jpg",
                                    'large': "http://cdn.dota2.com/apps/dota2/images/heroes/" + hero['name'][14::]  + "_lg.png" ,
                                    'icon' : "/static/images/miniheroes/" + hero['name'][14::]  + ".png" }
    return hero_image_dict

def get_matchids():
    """
    Returns list of matchids. Quantity: 'numberOfMatches'. Team: 'teamid'
    """
    matchList = []
    recentTeamMatches = (requests.get("https://api.opendota.com/api/teams/" + str(teamid) + "/matches")).json()[:numberOfMatches]    
    for match in recentTeamMatches:
        matchList.append(match['match_id'])

    return matchList


def get_match_info(matchid):
    """
    Returns dictionary with match information. dictionary format is as provided by opendota.
    """
    matchJSON = requests.get("https://api.opendota.com/api/matches/" + str(matchid)).json()

    #exit this function call if draft data is missing
    if not matchJSON["picks_bans"]:
        return
    curMatch = {}

    #teamA is the team we are searching for. teamB is their opponent in each match.
    if str(matchJSON["radiant_team_id"]) == str(teamid):
        isTeamARadiant = True
        curMatch["isTeamARadiant"] = True
    elif str(matchJSON["radiant_team_id"]) != str(teamid):
        isTeamARadiant = False
        curMatch["isTeamARadiant"] = False

    #get team logos
    if isTeamARadiant:
        curMatch['teamAlogo'], curMatch['teamBlogo'] = matchJSON["radiant_team"]["logo_url"], matchJSON["dire_team"]["logo_url"]
    else:
        curMatch['teamBlogo'], curMatch['teamAlogo'] = matchJSON["radiant_team"]["logo_url"], matchJSON["dire_team"]["logo_url"]

    #get team names
    if isTeamARadiant:
        curMatch['teamAname'], curMatch['teamBname'] = matchJSON["radiant_team"]["name"], matchJSON["dire_team"]["name"]
    else:
        curMatch['teamAname'], curMatch['teamBname'] = matchJSON["dire_team"]["name"], matchJSON["radiant_team"]["name"]

    #assign first pick
    if matchJSON["picks_bans"][0]["team"] == 0 and isTeamARadiant:
        curMatch['teamAfirstpick'] = True
    elif matchJSON["picks_bans"][0]["team"] == 1 and not isTeamARadiant:
        curMatch['teamAfirstpick'] = True
    else:
        curMatch['teamAfirstpick'] = False
        
        
    #get winner:
    if isTeamARadiant and matchJSON['radiant_win']:
        curMatch['teamAwin'], curMatch['teamBwin'] = True, False
    if isTeamARadiant and not matchJSON['radiant_win']:
        curMatch['teamAwin'], curMatch['teamBwin'] = False, True
    if not isTeamARadiant and matchJSON['radiant_win']:
        curMatch['teamAwin'], curMatch['teamBwin'] = False, True
    if not isTeamARadiant and not matchJSON['radiant_win']:
        curMatch['teamAwin'], curMatch['teamBwin'] = True, False

    #get start date of match
    curMatch["matchdate"] = datetime.fromtimestamp(matchJSON["start_time"]).strftime('%Y-%m-%d')

    #get radiant or dire win and assign to team 0 or team 1
    curMatch["draft"] = get_picks_bans(matchJSON["picks_bans"], isTeamARadiant)

    return curMatch

def get_picks_bans(picks_bans, isTeamARadiant):
    """
    returns draft information as dictionary
    """
    radiantpicks, radiantbans, direpicks, direbans = [], [], [], []
    
    for item in picks_bans:
        hero_id = item['hero_id']
        #team 0 is radiant and team 1 is dire
        if item["team"] == 0:
            if item["is_pick"]:
                radiantpicks.append(item)
            else:
                radiantbans.append(item)         
        elif item["team"] == 1:
            if item["is_pick"]:
                direpicks.append(item)
            else:
                direbans.append(item)

    #assign draft data to team according to radiant/dire
    if isTeamARadiant:
        match_draft = {
            "teamApicks": radiantpicks,
            "teamAbans": radiantbans,
            "teamBpicks": direpicks,
            "teamBbans": direbans
        }
    elif not isTeamARadiant:
         match_draft = {
            "teamApicks": direpicks,
            "teamAbans": direbans,
            "teamBpicks": radiantpicks,
            "teamBbans": radiantbans
        }   

    return match_draft

def produceHtmlFile(data, hero_image_dict):
    """
    Produces information in HTML format
    """

    htmlPage = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <link href="style.css" rel="stylesheet">
        <title>Draft Printout</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Open+Sans&display=swap" rel="stylesheet">
        <style>
        *{font-family:'Open Sans',sans-serif;text-align:left;margin:0;font-size:16px}body{width:21cm;height:27cm;padding:0 1cm;position:relative}@page{size:8.5in 11in}.draft{width:1400px}.team-draft{width:580px;display:inline-block}.ban,.pick{display:inline-block;position:relative;margin:1px}.sequence{font-size:16px;font-weight:700;position:absolute;z-index:100;padding:1px 2px;color:#fff}.pick .sequence{background-color:#437512}.ban .sequence{background-color:#b50000}.dire,.radiant{display:inline-block}.radiant{color:#92a525}.dire{color:#c23c2a}.match{margin-bottom:24px;padding-bottom:24px;border-bottom:1px solid grey;width:1150px;break-inside:avoid}.team-draft{margin-top:12px}.team-draft p{display:inline-block;vertical-align:middle;margin-bottom:4px}.teamlogo{height:24px;background:#000;padding:1px 4px;margin-right:4px;vertical-align:middle}.pick img{width:107px}.ban img{width:75px;filter:grayscale(100%)}.info-row b{font-weight:900;font-size:21px}.pagebreak{page-break-after:always}}
        </style>
        <body>
    """
    htmlBody = ""
    
    page_break_counter = 0

    for match in data:

        #winner string
        if data[match]['teamAwin']:
            teamAwinstring, teamBwinstring = ' / Winner', ''
        else:
            teamAwinstring, teamBwinstring = '', ' / Winner'

        #radiant or dire string
        if data[match]['isTeamARadiant']:
            teamAsidestring, teamBsidestring = 'Radiant', 'Dire'
        else:
            teamAsidestring, teamBsidestring = 'Dire', 'Radiant'

        #first pick / second pick string
        if data[match]['teamAfirstpick']:
            teamAprioritystring, teamBprioritystring = ' First Pick', ' Second Pick'
        else:
            teamAprioritystring, teamBprioritystring = ' Second Pick', ' First Pick'
            
        htmlBody += '<div class="match">\n'
        htmlBody += '<p> Match ID: ' + str(match) + ' Match Date: ' + str(data[match]['matchdate']) + '</p>\n'

        htmlBody += '<div class="draft">'
        #team A header
        htmlBody += '<div class="team-draft">\n'
        htmlBody += '<div class="info-row"><p><img alt="" class="teamlogo" src="' + data[match]['teamAlogo'] +'">' + data[match]['teamAname'] + ' / <b>' + teamAsidestring + teamAprioritystring + '</b>' +teamAwinstring + '</p></div>\n'

        #produce team A picks
        htmlBody += '<div class ="picks-row">\n'
        for pick in data[match]['draft']['teamApicks']:
            hero_id = pick['hero_id']
            htmlBody += '<div class="pick"><div class="sequence">' + str(pick["order"] + 1) + '</div><img alt="" src="' + str(hero_image_dict[hero_id]["large"]) + '"></div>\n'
        
        htmlBody += ' </div>\n'

        #produce team A bans
        htmlBody += '<div class ="bans-row">\n'
        for pick in data[match]['draft']['teamAbans']:
            hero_id = pick['hero_id']
            htmlBody += '<div class="ban"><div class="sequence">' + str(pick["order"] + 1) + '</div><img alt="" src="' + str(hero_image_dict[hero_id]["large"]) + '"></div>\n'

        htmlBody += ' </div></div>\n' #close team draft div and bans row
    
        #team B header
        htmlBody += '<div class="team-draft">\n'
        htmlBody += '<div class="info-row"><p><img alt="" class="teamlogo" src="' + data[match]['teamBlogo'] + '">' + data[match]['teamBname'] + ' / <b>' + teamBsidestring + teamBprioritystring + '</b>' + teamBwinstring + '</p></div>\n'
    
        #produce team B picks
        htmlBody += '<div class ="picks-row">\n'
        for pick in data[match]['draft']['teamBpicks']:
            hero_id = pick['hero_id']
            htmlBody += '<div class="pick"><div class="sequence">' + str(pick["order"] + 1) + '</div><img alt="" src="' + str(hero_image_dict[hero_id]["large"]) + '"></div>\n'

        htmlBody += ' </div>\n'

        #produce team B bans
        htmlBody += '<div class ="bans-row">\n'
        for pick in data[match]['draft']['teamBbans']:
            hero_id = pick['hero_id']
            htmlBody += '<div class="ban"><div class="sequence">' + str(pick["order"] + 1) + '</div><img alt="" src="' + str(hero_image_dict[hero_id]["large"]) + '"></div>\n'

        htmlBody += ' </div></div></div></div>\n' #close bans row, team draft, draft, and match divs

        # page breaks
        page_break_counter += 1
        if page_break_counter == 6:
            htmlBody += '''<div class="pagebreak"></div>'''
            page_break_counter = 0

    htmlPage += htmlBody
    htmlPage += """</body></html>"""
    
    date = datetime.today().strftime('%Y-%m-%d')
    filename = f'DraftPrintout{str(teamid)}--{date}.html'
    filedir = Path.cwd() / 'output'
    filedir.mkdir(mode=0o777, parents=True, exist_ok=True)
    filepath = filedir / filename
    print(filepath)

    f = open(filepath,'w')
    f.write(htmlPage)
    f.close()
    return filepath


def main():
    print("Getting match list...")
    matchList = get_matchids()
    hero_image_dict = get_imageDict()

    if not matchList:
        print("Error getting matchlist for team id: ", teamid, " Restart program and double check the number.")
        input("Press Enter or Close Window to Exit")
        quit()

    all_match_dict = {}
    for id in matchList:
        print("Getting Match Data For:", id)
        all_match_dict[id] = get_match_info(id)
        if all_match_dict[id] == None:
            print("Warning: Match Data missing for ", id, ". You will need to check if this match exists manually.")
            all_match_dict.pop(id)

    filepath = produceHtmlFile(all_match_dict, hero_image_dict)

    print(f"File created successfully at: {filepath}")
    print("When printing, set Margins to None and enable Background Graphics")
    input("Close Window to Exit. Good luck!")

main()

#Program written by Wilson Teng: wteng33@gmail.com