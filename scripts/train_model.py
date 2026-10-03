"""Train WinDrive's classifier from a reviewed, labelled CSV dataset.
The CSV must include all engineered columns in app.features.feature_engineer plus a classification column.
This script deliberately does not train from live scan output.
"""
import argparse, json, os, time, joblib, pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from app.features.feature_engineer import NUMERIC_FEATURES, CATEGORICAL_FEATURES, FEATURES, build_feature_rows

def main():
 p=argparse.ArgumentParser(); p.add_argument('dataset'); p.add_argument('--output',default='artifacts/models/driver_classifier.joblib'); args=p.parse_args()
 if args.dataset.lower().endswith('.json'):
  # Reviewed evidence records: driver, events, crashes, optional reference_time, classification.
  # This uses precisely the same feature function used by live scanning.
  with open(args.dataset, encoding='utf-8') as source: df=pd.DataFrame(build_feature_rows(json.load(source)))
 else: df=pd.read_csv(args.dataset)
 df=df.drop_duplicates(); required=set(FEATURES+['classification']); missing=required-set(df.columns)
 if missing: raise ValueError(f'Dataset is missing required fields: {sorted(missing)}')
 labels=df['classification'].str.lower(); invalid=set(labels)-{'normal','suspicious','faulty'}
 if invalid: raise ValueError(f'Invalid labels: {invalid}')
 x_train,x_test,y_train,y_test=train_test_split(df[FEATURES],labels,test_size=.2,random_state=42,stratify=labels)
 prep=ColumnTransformer([('number',Pipeline([('impute',SimpleImputer(strategy='median'))]),NUMERIC_FEATURES),('category',Pipeline([('impute',SimpleImputer(strategy='most_frequent')),('encode',OneHotEncoder(handle_unknown='ignore'))]),CATEGORICAL_FEATURES)])
 pipeline=Pipeline([('preprocessing',prep),('model',RandomForestClassifier(n_estimators=300,random_state=42,class_weight='balanced'))]); started=time.time();pipeline.fit(x_train,y_train); predicted=pipeline.predict(x_test)
 metrics={'accuracy':accuracy_score(y_test,predicted),'classification_report':classification_report(y_test,predicted,output_dict=True),'confusion_matrix':confusion_matrix(y_test,predicted,labels=['normal','suspicious','faulty']).tolist(),'processing_time_seconds':time.time()-started,'test_rows':len(x_test)}
 os.makedirs(os.path.dirname(args.output),exist_ok=True); joblib.dump({'pipeline':pipeline,'classes':list(pipeline.classes_),'feature_schema':FEATURES,'model_version':'1.0','metrics':metrics},args.output)
 print(json.dumps(metrics,indent=2))
if __name__=='__main__': main()
