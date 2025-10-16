import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
import time
import base64

# Configuration de la page
st.set_page_config(
    page_title="EduEval - Alternative Tactiléo",
    page_icon="🎓",
    layout="wide"
)

class PDFProcessor:
    def extract_text(self, uploaded_file):
        """Extrait le texte d'un PDF uploadé"""
        try:
            import PyPDF2
            import pdfplumber
            
            # Sauvegarde temporaire
            with open("temp.pdf", "wb") as f:
                f.write(uploaded_file.getvalue())
            
            text = ""
            # Essai avec pdfplumber
            try:
                with pdfplumber.open("temp.pdf") as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            except:
                # Fallback avec PyPDF2
                with open("temp.pdf", "rb") as file:
                    reader = PyPDF2.PdfReader(file)
                    for page in reader.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            
            # Nettoyage
            if os.path.exists("temp.pdf"):
                os.remove("temp.pdf")
                
            return text.strip() if text else None
            
        except Exception as e:
            st.error(f"Erreur lors de l'extraction: {str(e)}")
            return None

class QuestionGenerator:
    def __init__(self):
        self.question_templates = [
            "Qu'est-ce que {concept} ?",
            "Quelle est la définition de {concept} ?",
            "Quel est le rôle de {concept} ?",
            "Quelles sont les caractéristiques de {concept} ?"
        ]
    
    def extract_concepts(self, text):
        """Extrait les concepts importants"""
        import re
        sentences = re.split(r'[.!?]', text)
        concepts = []
        
        for sentence in sentences:
            words = sentence.strip().split()
            if len(words) > 3:
                for word in words:
                    clean_word = re.sub(r'[^\w\s]', '', word)
                    if (clean_word.istitle() or len(clean_word) > 7) and clean_word not in concepts:
                        concepts.append(clean_word)
        
        return concepts[:15]
    
    def generate_from_text(self, text):
        """Génère des questions à partir du texte"""
        import random
        concepts = self.extract_concepts(text)
        questions = []
        
        if len(concepts) < 2:
            return questions
        
        for i in range(min(8, len(concepts))):
            template = random.choice(self.question_templates)
            concept = random.choice(concepts)
            question_text = template.format(concept=concept)
            
            # Options de réponse
            correct_option = f"Réponse correcte pour {concept}"
            wrong_options = [f"Option alternative {j+1}" for j in range(3)]
            
            options = [correct_option] + wrong_options
            random.shuffle(options)
            correct_index = options.index(correct_option) + 1
            
            questions.append({
                'question': question_text,
                'options': options,
                'correct': correct_index,
                'type': 'qcm'
            })
        
        return questions

class EvaluationManager:
    def __init__(self):
        self.evaluations = []
        self.results = []
    
    def save_evaluation(self, evaluation):
        """Sauvegarde une évaluation"""
        self.evaluations.append(evaluation)
        return True
    
    def get_evaluations(self):
        """Récupère toutes les évaluations"""
        return self.evaluations
    
    def save_result(self, result_data):
        """Sauvegarde un résultat"""
        self.results.append(result_data)
        return True
    
    def get_all_results(self):
        """Récupère tous les résultats"""
        return self.results

def main():
    # Initialisation
    if 'eval_manager' not in st.session_state:
        st.session_state.eval_manager = EvaluationManager()
    if 'pdf_processor' not in st.session_state:
        st.session_state.pdf_processor = PDFProcessor()
    if 'question_gen' not in st.session_state:
        st.session_state.question_gen = QuestionGenerator()
    
    # Sidebar
    st.sidebar.title("🎓 EduEval")
    st.sidebar.markdown("---")
    
    menu = st.sidebar.radio(
        "Navigation",
        ["📊 Dashboard", "📚 Importer Cours", "🎯 Créer Évaluation", 
         "📝 Passer Évaluation", "📈 Résultats"]
    )
    
    # Pages
    if menu == "📊 Dashboard":
        show_dashboard()
    elif menu == "📚 Importer Cours":
        import_course()
    elif menu == "🎯 Créer Évaluation":
        create_evaluation()
    elif menu == "📝 Passer Évaluation":
        take_evaluation()
    elif menu == "📈 Résultats":
        show_results()

def show_dashboard():
    st.title("📊 Tableau de Bord EduEval")
    
    manager = st.session_state.eval_manager
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Évaluations créées", len(manager.get_evaluations()))
    with col2:
        st.metric("Résultats enregistrés", len(manager.get_all_results()))
    with col3:
        st.metric("Questions générées", sum(len(eval['questions']) for eval in manager.get_evaluations()))
    
    # Évaluations récentes
    st.subheader("📋 Évaluations disponibles")
    evaluations = manager.get_evaluations()
    if evaluations:
        for eval in evaluations:
            with st.expander(f"🎯 {eval['name']} - {len(eval['questions'])} questions"):
                st.write(f"Créée le : {eval.get('created_at', 'N/A')}")
                if st.button("Voir détails", key=f"view_{eval['name']}"):
                    st.write("Questions :")
                    for q in eval['questions']:
                        st.write(f"- {q['question']}")
    else:
        st.info("Aucune évaluation créée pour le moment")

def import_course():
    st.title("📚 Importer un Cours PDF")
    
    uploaded_file = st.file_uploader("Choisissez un fichier PDF", type="pdf")
    
    if uploaded_file is not None:
        with st.spinner("Extraction du contenu..."):
            text_content = st.session_state.pdf_processor.extract_text(uploaded_file)
        
        if text_content:
            st.success("✅ PDF importé avec succès !")
            
            # Aperçu
            with st.expander("📄 Aperçu du contenu (premières 1500 caractères)"):
                st.text(text_content[:1500] + "..." if len(text_content) > 1500 else text_content)
            
            # Génération de questions
            if st.button("🔄 Générer des questions automatiquement"):
                with st.spinner("Génération des questions..."):
                    questions = st.session_state.question_gen.generate_from_text(text_content)
                
                if questions:
                    st.session_state.generated_questions = questions
                    st.success(f"✅ {len(questions)} questions générées !")
                    
                    st.subheader("Questions générées :")
                    for i, q in enumerate(questions):
                        st.write(f"**Q{i+1}:** {q['question']}")
                        st.write(f"Options: {', '.join(q['options'])}")
                        st.write(f"Réponse correcte: {q['correct']}")
                        st.write("---")
                else:
                    st.warning("❌ Aucune question générée. Le document est peut-être trop court.")

def create_evaluation():
    st.title("🎯 Créer une Évaluation")
    
    # Nom de l'évaluation
    eval_name = st.text_input("Nom de l'évaluation")
    
    # Questions disponibles
    available_questions = st.session_state.get('generated_questions', [])
    
    if available_questions:
        st.subheader("Questions disponibles")
        selected_questions = []
        
        for i, q in enumerate(available_questions):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"**{q['question']}**")
                for j, opt in enumerate(q['options']):
                    st.write(f"  {j+1}. {opt}")
            with col2:
                if st.checkbox("Sélectionner", key=f"sel_{i}"):
                    selected_questions.append(q)
        
        # Configuration
        if selected_questions and eval_name:
            st.subheader("⚙️ Configuration")
            
            col1, col2 = st.columns(2)
            with col1:
                time_per_q = st.number_input("Temps par question (secondes)", 30, 300, 60)
                shuffle = st.checkbox("Mélanger les questions", True)
            with col2:
                show_results = st.checkbox("Afficher résultats immédiats", True)
                max_attempts = st.number_input("Tentatives max", 1, 5, 1)
            
            if st.button("💾 Sauvegarder l'évaluation"):
                evaluation = {
                    'name': eval_name,
                    'questions': selected_questions,
                    'settings': {
                        'time_per_question': time_per_q,
                        'shuffle_questions': shuffle,
                        'show_results': show_results,
                        'max_attempts': max_attempts
                    },
                    'created_at': datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                
                if st.session_state.eval_manager.save_evaluation(evaluation):
                    st.success("✅ Évaluation sauvegardée !")
                    # Réinitialiser
                    if 'generated_questions' in st.session_state:
                        del st.session_state.generated_questions
    else:
        st.info("ℹ️ Importez d'abord un cours PDF pour générer des questions")

def take_evaluation():
    st.title("📝 Passer une Évaluation")
    
    # Identification
    student_id = st.text_input("Votre identifiant étudiant")
    
    # Sélection évaluation
    evaluations = st.session_state.eval_manager.get_evaluations()
    
    if not evaluations:
        st.info("ℹ️ Aucune évaluation disponible")
        return
    
    eval_names = [e['name'] for e in evaluations]
    selected_eval = st.selectbox("Choisir une évaluation", eval_names)
    
    if selected_eval and student_id:
        if st.button("🚀 Commencer l'évaluation"):
            evaluation = next(e for e in evaluations if e['name'] == selected_eval)
            st.session_state.current_eval = evaluation
            st.session_state.student_id = student_id
            st.session_state.current_q = 0
            st.session_state.responses = []
            st.session_state.start_time = time.time()
            st.session_state.completed = False
            st.experimental_rerun()

def evaluation_interface():
    if 'current_eval' not in st.session_state:
        return
    
    eval_data = st.session_state.current_eval
    student_id = st.session_state.student_id
    current_q = st.session_state.current_q
    responses = st.session_state.responses
    
    if st.session_state.get('completed', False):
        show_eval_results(eval_data, student_id, responses)
        return
    
    # Header
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**Étudiant:** {student_id}")
    with col2:
        st.write(f"**Question:** {current_q + 1}/{len(eval_data['questions'])}")
    with col3:
        elapsed = int(time.time() - st.session_state.start_time)
        st.write(f"**Temps:** {elapsed}s")
    
    st.markdown("---")
    
    # Question actuelle
    question = eval_data['questions'][current_q]
    
    st.subheader(f"Question {current_q + 1}")
    st.write(question['question'])
    
    # Réponses
    selected = st.radio("Choisissez :", question['options'], key=f"q{current_q}")
    
    # Navigation
    col1, col2 = st.columns(2)
    
    with col1:
        if current_q > 0 and st.button("← Précédent"):
            st.session_state.current_q -= 1
            st.experimental_rerun()
    
    with col2:
        if current_q < len(eval_data['questions']) - 1:
            if st.button("Suivant →"):
                responses.append({
                    'question_idx': current_q,
                    'selected': selected,
                    'correct': selected == question['options'][question['correct'] - 1]
                })
                st.session_state.current_q += 1
                st.experimental_rerun()
        else:
            if st.button("🏁 Terminer"):
                responses.append({
                    'question_idx': current_q,
                    'selected': selected,
                    'correct': selected == question['options'][question['correct'] - 1]
                })
                st.session_state.completed = True
                st.experimental_rerun()

def show_eval_results(eval_data, student_id, responses):
    st.title("📊 Résultats")
    
    # Calcul score
    correct = sum(1 for r in responses if r['correct'])
    total = len(eval_data['questions'])
    percentage = (correct / total) * 100
    
    st.metric("Score final", f"{correct}/{total} ({percentage:.1f}%)")
    
    # Détail
    st.subheader("Détail des réponses")
    for i, resp in enumerate(responses):
        q = eval_data['questions'][i]
        col1, col2, col3 = st.columns([3, 1, 2])
        
        with col1:
            st.write(f"**{q['question']}**")
        
        with col2:
            if resp['correct']:
                st.success("✓ Correct")
            else:
                st.error("✗ Incorrect")
        
        with col3:
            st.write(f"Votre réponse: {resp['selected']}")
            if not resp['correct']:
                correct_ans = q['options'][q['correct'] - 1]
                st.write(f"Bonne réponse: {correct_ans}")
    
    # Sauvegarde
    result_data = {
        'student_id': student_id,
        'evaluation_name': eval_data['name'],
        'score': correct,
        'total': total,
        'percentage': percentage,
        'completed_at': datetime.now().strftime("%Y-%m-%d %H:%M")
    }
    
    st.session_state.eval_manager.save_result(result_data)
    
    if st.button("📋 Retour au menu"):
        for key in ['current_eval', 'student_id', 'current_q', 'responses', 'completed']:
            if key in st.session_state:
                del st.session_state[key]
        st.experimental_rerun()

def show_results():
    st.title("📈 Résultats des Évaluations")
    
    results = st.session_state.eval_manager.get_all_results()
    
    if not results:
        st.info("Aucun résultat disponible")
        return
    
    # Tableau
    df_data = []
    for res in results:
        df_data.append({
            'Étudiant': res['student_id'],
            'Évaluation': res['evaluation_name'],
            'Score': f"{res['score']}/{res['total']}",
            'Pourcentage': f"{res['percentage']:.1f}%",
            'Date': res['completed_at']
        })
    
    if df_data:
        df = pd.DataFrame(df_data)
        st.dataframe(df)
        
        # Export
        csv = df.to_csv(index=False)
        st.download_button(
            "📥 Télécharger en CSV",
            csv,
            "resultats_evaluations.csv",
            "text/csv"
        )

# Gestion de l'interface d'évaluation
if 'current_eval' in st.session_state:
    evaluation_interface()
else:
    main()
