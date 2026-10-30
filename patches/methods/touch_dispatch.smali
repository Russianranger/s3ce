.method public onTouchEvent(Landroid/view/MotionEvent;)Z
    .locals 2
    # S3CE: record before native dispatch, and never sleep the UI input thread.
    invoke-static {p1}, Lcom/ideaworks3d/thesims3/GameDiagnostics;->touch(Landroid/view/MotionEvent;)V
    iget-boolean v0, p0, Lcom/ideaworks3d/airplay/AirplayView;->m_InputTextRunning:Z
    if-eqz v0, :s3ce_dispatch
    # Dialog takeover still needs to release the gesture it just cancelled.
    invoke-virtual {p1}, Landroid/view/MotionEvent;->getActionMasked()I
    move-result v0
    const/4 v1, 0x3
    if-eq v0, v1, :s3ce_dispatch
    const/4 v0, 0x0
    return v0
    :s3ce_dispatch
    invoke-static {p0, p1}, Lcom/ideaworks3d/airplay/MultiTouch;->onTouchEvent(Lcom/ideaworks3d/airplay/AirplayView;Landroid/view/MotionEvent;)Z
    move-result v0
    return v0
.end method
