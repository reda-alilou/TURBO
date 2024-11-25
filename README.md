# **TURBO Bot for Discord**

## **Description**
TURBO est un bot Discord automatisé développé en Python. Il offre une variété de fonctionnalités adaptées à la gestion de serveurs Discord, y compris la modération automatique, des jeux interactifs, un système de niveaux et points, des services utilitaires comme la météo, et bien plus encore.

---

## **Fonctionnalités**
### **1. Modération :**
- **Détection de mots interdits** : Supprime automatiquement les messages contenant des mots interdits.
- **Gestion des liens autorisés/non autorisés** : Supprime les liens qui ne proviennent pas de domaines approuvés.
- **Commandes d'administration :**
  - `!ban [membre] [raison]` : Bannit un membre.
  - `!kick [membre] [raison]` : Expulse un membre.
  - `!unban [utilisateur]` : Réintègre un utilisateur banni.
  - `!timeout [membre] [durée]` : Importe un timeout temporaire (ex. `10m`, `2h`).

### **2. Bienvenue :**
- Envoie un message de bienvenue personnalisé dans le canal `👋welcome`.
- Attribue automatiquement le rôle "Member" aux nouveaux arrivants.

### **3. Jeux interactifs :**
- **Quiz interactif :**
  - `!start_quiz [catégorie] [difficulté]` : Démarre un quiz avec des questions tirées d'une API.
  - `!end_quiz` : Termine le quiz en cours.
  - `!quiz_categories` : Affiche les catégories disponibles.

### **4. Système de niveaux :**
- Chaque message envoyé augmente les points d'un utilisateur.
- Les utilisateurs reçoivent une notification lorsqu'ils montent de niveau.
- Commandes associées :
  - `!mon_niveau` : Affiche le niveau et les points d'un utilisateur.
  - `!leaderboard` : Affiche le classement des utilisateurs par points.

### **5. Fonctionnalités utilitaires :**
- **Météo :**
  - `!weather [city]` : Affiche les informations météo actuelles pour une ville donnée.

### **6. Rôles via réactions :**
- Les utilisateurs peuvent attribuer ou retirer des rôles via des réactions dans le canal `⭕roles`.

### **7. Divers :**
- `!hello` : Vérifie si le bot est actif.
- `!blague` : Récupère une blague depuis une API.
- `!meme` : Affiche un meme aléatoire.

---

## **Important : Configuration des Noms des Canaux**
Pour utiliser ce bot dans un autre serveur Discord, vous devez remplacer les noms des canaux (par exemple, `👋welcome`, `📬logs`, `⭕roles`) dans le code source par les noms des canaux correspondants dans le serveur cible.

---

## **Installation**

### **Prérequis :**
- Python 3.10 ou plus récent.
- Les dépendances listées dans le fichier `requirements.txt`.

### **Étapes détaillées d'installation :**

1. **Clonez ce dépôt :**
   ```bash
   git clone https://github.com/votre-repo/turbo-bot.git
   cd turbo-bot
   ```

2. **Créez un environnement virtuel :**
   - Sur **Linux/macOS** :
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```
   - Sur **Windows** :
     ```bash
     python -m venv venv
     venv\Scripts\activate
     ```

3. **Installez les dépendances nécessaires :**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ajoutez un fichier `.env` pour les clés d'API et le token du bot :**
   Créez un fichier nommé `.env` à la racine du projet et ajoutez-y les informations suivantes :
   ```env
   TURBO_TOKEN=votre_token_discord
   OPENWEATHER_API_KEY=votre_clé_api_openweather
   ```

5. **Modifiez les noms des canaux dans le code source :**
   Ouvrez `turbo.py` et remplacez les noms des canaux (`👋welcome`, `📬logs`, etc.) par les noms des canaux de votre serveur Discord.

6. **Lancez le bot :**
   ```bash
   python turbo.py
   ```

---

## **Utilisation**

1. **Invitez le bot sur votre serveur Discord :**
   Générez un lien OAuth2 dans le [Portail des développeurs Discord](https://discord.com/developers/applications) et invitez le bot sur votre serveur.

2. **Configurez les permissions et les rôles nécessaires.**

3. **Utilisez les commandes disponibles avec le préfixe `!`.**

---

## **Contributeurs**
- **Reda Alilou**
