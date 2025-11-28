export path=`pwd`
cd /home/wyc/save_improvement_file/solution_saving/
rm -rf *.txt
cd /home/wyc/save_improvement_file/edited_code_saving/
rm -rf *.rs
cd /home/wyc/save_improvement_file/failure/
rm -rf *.rs
cd /home/wyc/save_improvement_file/pass/
rm -rf *.rs
cd /home/wyc/save_improvement_file/score_recording/
rm -rf *.txt
cd /home/wyc/save_improvement_file/evaluation_wave/
rm -rf *.png
cd $path
echo "===State Machine Running==="
python3 State_Machine.py

