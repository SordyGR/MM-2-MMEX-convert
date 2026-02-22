# MM-2-MMEX-convert
Money Manager (android app) to Money Manager EX Converter

This is provided as is, it was developed with LLMs ChatGPT, Deepseek and such
Keep in mind: My CSV files follow my loacale that uses ";" as separator of columns in CSV isntead of "," (you need to change the code provided to your separator)

Workflow goes like this
1. Get your xlsx from Money Manager app
2. Open the file and edit you G column to have " . " as decimal separator manually (manually select range --> ctrl+f --> tab replace [Find , | replace with .])
3. Split it with the xlsx splitter (in excel alt+f11 --> Insert --> Module --> paste the code)
4. now you should have 2 csv file ( one contains the transactions the other one has the transfers)
5. Run the importers on the splitted files in any order and follow the pop windos headers: first you choose the your DB file (.mmb) then your .CSV
6. you should be done, hopefully!
