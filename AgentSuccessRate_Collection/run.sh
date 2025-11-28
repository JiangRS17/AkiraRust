export path=`pwd`
cd /home/wyc/save_defect_curve/defect_recording/
rm -rf *.txt
cd /home/wyc/save_defect_curve/solution_saving/
rm -rf *.txt
cd /home/wyc/save_defect_curve/edited_code_saving/
rm -rf *
cd /home/wyc/save_defect_curve/failure/
rm -rf *.rs
cd /home/wyc/save_defect_curve/pass/
rm -rf *.rs
cd /home/wyc/save_defect_curve/score_recording/
rm -rf *
cd $path
echo "Fast Thinking:"
python3 Defect_Fast_Thinking.py
echo "Slow Thinking:"
python3 Defect_Slow_Thinking.py
echo "Code Evaluating:"
python3 Defect_Code_Evaluate.py
