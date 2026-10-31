.method public compatGlInit(I)V
    .locals 3
    # A typed JNI entry that retains the exact original private GL lifecycle.
    iget-boolean v0, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_UseGL:Z
    iget-object v1, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_Paused:Ljava/lang/Boolean;
    iget-object v2, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_Terminating:Ljava/lang/Boolean;
    invoke-static {p1, v0, v1, v2}, Lcom/ideaworks3d/thesims3/GameDiagnostics;->recordGlEntry(IZLjava/lang/Object;Ljava/lang/Object;)V
    :s3ce_gl_try
    invoke-direct {p0, p1}, Lcom/ideaworks3d/airplay/AirplayThread;->glInit(I)V
    :s3ce_gl_end
    .catch Ljava/lang/Throwable; {:s3ce_gl_try .. :s3ce_gl_end} :s3ce_gl_failed
    iget-boolean v0, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_UseGL:Z
    iget-object v1, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_Paused:Ljava/lang/Boolean;
    iget-object v2, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_Terminating:Ljava/lang/Boolean;
    invoke-static {p1, v0, v1, v2}, Lcom/ideaworks3d/thesims3/GameDiagnostics;->recordGlExit(IZLjava/lang/Object;Ljava/lang/Object;)V
    return-void
    :s3ce_gl_failed
    move-exception v0
    invoke-static {v0}, Lcom/ideaworks3d/thesims3/GameDiagnostics;->recordGlFailure(Ljava/lang/Throwable;)V
    throw v0
.end method
